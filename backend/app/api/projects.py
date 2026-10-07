import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db import get_session
from app.languages import DEFAULT_SOURCE_LANGUAGE
from app.models.project import Document, DocumentPage, DocumentSegment, Project
from app.parsers.pdf import PdfError, parse_pdf
from app.schemas.project import ProjectResponse, ProjectUpdateRequest, TranslateRequest
from app.services.language_detection import detect_primary_language, is_translatable
from app.services.translation_service import run_document_translation

router = APIRouter(prefix="/projects", tags=["projects"])


async def _get_project_or_404(project_id: uuid.UUID, db_session: AsyncSession) -> Project:
    """
    Fetch a Project by its UUID, including its related documents, pages, and segments.

    Args:
        project_id: The UUID of the project to retrieve.
        db_session: The active asynchronous database session.

    Returns:
        The fully loaded Project ORM object.

    Raises:
        HTTPException: 404 if the project does not exist.
    """
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.documents).selectinload(Document.pages),
            selectinload(Project.documents).selectinload(Document.segments),
        )
    )
    result = await db_session.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    file: Annotated[UploadFile, File(...)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    """
    Upload a PDF, parse its contents, detect languages, and create a new project.

    Args:
        file: The uploaded PDF file payload.
        db_session: The active asynchronous database session.

    Returns:
        ProjectResponse containing the new project's metadata, parsed pages, and segments.

    Raises:
        HTTPException: 400 for missing filename or bad PDF, 500 for unhandled parsing errors.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    pdf_bytes = await file.read()
    try:
        parsed_doc = parse_pdf(pdf_bytes)
    except PdfError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while parsing the PDF."
        ) from e

    upload_dir = Path(get_settings().upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    project_name = Path(file.filename).stem
    project = Project(name=project_name)
    db_session.add(project)
    await db_session.flush()

    file_ext = Path(file.filename).suffix
    file_path = upload_dir / f"{project.id}{file_ext}"

    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    source_language = DEFAULT_SOURCE_LANGUAGE

    document = Document(
        project_id=project.id,
        original_filename=file.filename,
        file_path=str(file_path),
        source_language=source_language,
    )
    db_session.add(document)
    await db_session.flush()

    for page in parsed_doc.pages:
        db_page = DocumentPage(
            document_id=document.id,
            number=page.number,
            width=page.width,
            height=page.height,
            warnings=list(page.warnings),
        )
        db_session.add(db_page)

    order_index = 0
    for segment in parsed_doc.segments:
        detected = detect_primary_language(segment.text)
        translatable = is_translatable(segment.text, source_language)

        db_segment = DocumentSegment(
            document_id=document.id,
            page_number=segment.page,
            order_index=order_index,
            kind=segment.kind,
            text=segment.text,
            bounding_box=list(segment.bbox),
            detected_language=detected,
            is_translatable=translatable,
        )
        db_session.add(db_segment)
        order_index += 1

    await db_session.commit()
    return ProjectResponse.model_validate(await _get_project_or_404(project.id, db_session))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    """
    Get a project and all its parsed contents.

    Args:
        project_id: The UUID of the project to retrieve.
        db_session: The active asynchronous database session.

    Returns:
        ProjectResponse representing the requested project.
    """
    return ProjectResponse.model_validate(await _get_project_or_404(project_id, db_session))


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    """
    Update a project, typically to confirm or change its source language.

    Changing the source language recalculates the 'is_translatable' flag
    for every segment in the project.

    Args:
        project_id: The UUID of the project to update.
        payload: ProjectUpdateRequest containing the new source language.
        db_session: The active asynchronous database session.

    Returns:
        ProjectResponse representing the updated project.
    """
    project = await _get_project_or_404(project_id, db_session)

    # In MVP, a project has 1 document. We update the source language and recalculate.
    for doc in project.documents:
        doc.source_language = payload.source_language
        for segment in doc.segments:
            segment.is_translatable = is_translatable(segment.text, payload.source_language)

    await db_session.commit()
    # Refresh to ensure we return the latest state
    return ProjectResponse.model_validate(await _get_project_or_404(project_id, db_session))


@router.post("/{project_id}/translate", status_code=status.HTTP_202_ACCEPTED)
async def translate_project(
    project_id: uuid.UUID,
    payload: TranslateRequest,
    background_tasks: BackgroundTasks,
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """
    Trigger the translation of a project.

    This endpoint returns immediately (202 Accepted) while the translation
    orchestrator processes the document segments in the background.

    Args:
        project_id: The UUID of the project to translate.
        payload: TranslateRequest containing the target language code.
        background_tasks: FastAPI BackgroundTasks runner.
        db_session: The active asynchronous database session.

    Returns:
        A dictionary containing a success message indicating background processing started.

    Raises:
        HTTPException: 400 if the project has no documents or is missing a source language.
    """
    project = await _get_project_or_404(project_id, db_session)

    if not project.documents:
        raise HTTPException(status_code=400, detail="Project has no documents to translate.")

    document = project.documents[0]
    if not document.source_language:
        raise HTTPException(
            status_code=400, detail="Document source language must be set before translation."
        )

    background_tasks.add_task(
        run_document_translation, document_id=document.id, target_language=payload.target_language
    )

    return {"message": "Translation started in the background."}
