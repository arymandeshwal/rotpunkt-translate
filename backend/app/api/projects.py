import shutil
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
from app.schemas.project import ProjectResponse
from app.services.language_detection import detect_primary_language, is_translatable

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    file: Annotated[UploadFile, File(...)],
    db_session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectResponse:
    """Upload a PDF, parse its contents, detect languages, and create a new project."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")
    
    # 1. Read and parse the PDF
    pdf_bytes = await file.read()
    try:
        parsed_doc = parse_pdf(pdf_bytes)
    except PdfError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while parsing the PDF."
        )

    # 2. Save the file to disk
    upload_dir = Path(get_settings().upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Create the project first to get a UUID for the file path
    project_name = Path(file.filename).stem
    project = Project(name=project_name)
    db_session.add(project)
    await db_session.flush() # flush to get project.id
    
    file_ext = Path(file.filename).suffix
    file_path = upload_dir / f"{project.id}{file_ext}"
    
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)
        
    # 3. Create Document and its children
    # We use a default source language initially; the user confirms it in Step 3d
    source_language = DEFAULT_SOURCE_LANGUAGE
    
    document = Document(
        project_id=project.id,
        original_filename=file.filename,
        file_path=str(file_path),
        source_language=source_language,
    )
    db_session.add(document)
    await db_session.flush() # flush to get document.id

    # Populate Pages
    for page in parsed_doc.pages:
        db_page = DocumentPage(
            document_id=document.id,
            number=page.number,
            width=page.width,
            height=page.height,
            warnings=list(page.warnings),
        )
        db_session.add(db_page)

    # Populate Segments
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

    # 4. Commit and return
    await db_session.commit()
    
    # Reload the project with its documents, pages, and segments to return the full schema
    stmt = (
        select(Project)
        .where(Project.id == project.id)
        .options(
            selectinload(Project.documents).selectinload(Document.pages),
            selectinload(Project.documents).selectinload(Document.segments),
        )
    )
    result = await db_session.execute(stmt)
    full_project = result.scalar_one()
    
    return full_project
