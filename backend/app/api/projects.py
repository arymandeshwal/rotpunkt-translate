import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.config import get_settings
from app.db import get_session
from app.languages import DEFAULT_SOURCE_LANGUAGE
from app.models.project import Document, DocumentPage, DocumentSegment, Project
from app.parsers.pdf import PdfError, parse_pdf
from app.schemas.project import ProjectResponse, ProjectUpdateRequest
from app.services.language_detection import detect_primary_language, is_translatable

router = APIRouter(prefix="/projects", tags=["projects"])


async def _get_project_or_404(project_id: uuid.UUID, db_session: AsyncSession) -> Project:
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
    """Upload a PDF, parse its contents, detect languages, and create a new project."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")
    
    pdf_bytes = await file.read()
    try:
        parsed_doc = parse_pdf(pdf_bytes)
    except PdfError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while parsing the PDF."
        )

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
    return await _get_project_or_404(project.id, db_session)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    """Get a project and all its parsed contents."""
    return await _get_project_or_404(project_id, db_session)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    """Update a project, typically to confirm or change its source language.
    
    Changing the source language recalculates the 'is_translatable' flag
    for every segment in the project.
    """
    project = await _get_project_or_404(project_id, db_session)
    
    # In MVP, a project has 1 document. We update the source language and recalculate.
    for doc in project.documents:
        doc.source_language = payload.source_language
        for segment in doc.segments:
            segment.is_translatable = is_translatable(segment.text, payload.source_language)
            
    await db_session.commit()
    # Refresh to ensure we return the latest state
    return await _get_project_or_404(project_id, db_session)
