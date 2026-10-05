import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Document, DocumentPage, DocumentSegment, Project, ProjectStatus


async def test_project_defaults(db_session: AsyncSession) -> None:
    """Test that a project gets correct defaults for ID, timestamps, and status."""
    project = Project(name="Test Project")
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    assert project.id is not None
    assert project.status == ProjectStatus.NEW
    assert project.created_at is not None
    assert project.updated_at is not None


async def test_document_and_children_cascade(db_session: AsyncSession) -> None:
    """Test that creating a document persists its pages and segments, and deleting it cleans up."""
    project = Project(name="Upload Test")
    db_session.add(project)
    await db_session.commit()
    
    doc = Document(
        project_id=project.id,
        original_filename="test.pdf",
        file_path="uploads/test.pdf",
        source_language="de",
        pages=[
            DocumentPage(number=1, width=595.0, height=842.0, warnings=["no_text_layer"]),
        ],
        segments=[
            DocumentSegment(
                page_number=1,
                order_index=0,
                kind="heading",
                text="Rotpunkt Küchen",
                bounding_box=[10.0, 10.0, 100.0, 20.0],
                detected_language="de",
                is_translatable=True,
            )
        ]
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    
    assert doc.id is not None
    assert len(doc.pages) == 1
    assert doc.pages[0].warnings == ["no_text_layer"]
    assert len(doc.segments) == 1
    assert doc.segments[0].detected_language == "de"
    
    # Test cascade delete
    doc_id = doc.id
    await db_session.delete(doc)
    await db_session.commit()
    
    result_pages = await db_session.scalars(select(DocumentPage).where(DocumentPage.document_id == doc_id))
    assert len(result_pages.all()) == 0
    
    result_segments = await db_session.scalars(select(DocumentSegment).where(DocumentSegment.document_id == doc_id))
    assert len(result_segments.all()) == 0
