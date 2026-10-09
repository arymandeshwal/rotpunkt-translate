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
from app.schemas.project import (
    DocumentSegmentSchema,
    ProjectResponse,
    ProjectUpdateRequest,
    TranslateRequest,
)
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


@router.post(
    "/{project_id}/segments/{segment_id}/retranslate",
    response_model=DocumentSegmentSchema,
    status_code=status.HTTP_200_OK,
)
async def retranslate_segment(
    project_id: uuid.UUID,
    segment_id: uuid.UUID,
    payload: TranslateRequest,
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentSegment:
    """
    Re-translate a single document segment synchronously.

    Args:
        project_id: The UUID of the project.
        segment_id: The UUID of the segment to re-translate.
        payload: TranslateRequest containing the target language code.
        db_session: The active asynchronous database session.

    Returns:
        The updated DocumentSegment object.

    Raises:
        HTTPException: 404 if the project or segment is not found.
        HTTPException: 400 if the document has no source language or segment is not translatable.
    """
    from app.services.highlighting import compute_deterministic_annotations
    from app.services.jev_annotator import compute_ai_annotations
    from app.services.qa_checks import compute_qa_issues
    from app.services.translation.factory import get_translation_provider
    from app.services.translation_service import get_glossary_for_languages

    # 1. Fetch the project and document
    project = await _get_project_or_404(project_id, db_session)
    if not project.documents:
        raise HTTPException(status_code=400, detail="Project has no documents.")

    document = project.documents[0]
    if not document.source_language:
        raise HTTPException(status_code=400, detail="Document source language must be set.")

    # 2. Fetch the specific segment
    segment = None
    for seg in document.segments:
        if seg.id == segment_id:
            segment = seg
            break

    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found.")

    if not segment.is_translatable:
        raise HTTPException(status_code=400, detail="Segment is not translatable.")

    target_lang = payload.target_language
    provider = get_translation_provider()

    # 3. Fetch glossary and translate
    glossary_infos = await get_glossary_for_languages(
        db_session, document.source_language, target_lang
    )
    master_glossary = {item.source_text: item.target_text for item in glossary_infos}

    translated_texts = await provider.translate(
        texts=[segment.text],
        source_language=document.source_language,
        target_language=target_lang,
        glossary=master_glossary,
    )

    new_translation = translated_texts[0]

    # 4. Compute annotations
    ai_annotations_batch = await compute_ai_annotations([new_translation])
    ai_annotations = ai_annotations_batch[0]
    det_annotations = compute_deterministic_annotations(new_translation, glossary_infos)

    new_annotations = det_annotations + ai_annotations
    new_annotations.sort(key=lambda x: x["start"])

    # 5. Update DB
    # We must explicitly create new dicts so SQLAlchemy detects the mutation on the JSON column
    current_translations = dict(segment.translations or {})
    current_translations[target_lang] = new_translation
    segment.translations = current_translations

    current_annotations = dict(segment.annotations or {})
    current_annotations[target_lang] = new_annotations
    segment.annotations = current_annotations

    # Compute QA issues
    issues = compute_qa_issues(
        segment.text, new_translation, glossary_infos, segment.is_translatable
    )
    current_issues = dict(segment.issues or {})
    current_issues[target_lang] = issues
    segment.issues = current_issues

    await db_session.commit()

    # Return the segment (it will be serialized by Pydantic response_model)
    return segment


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
