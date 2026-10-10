import pytest
import uuid
from httpx import AsyncClient
from app.models.project import Project, Document, DocumentPage, DocumentSegment, ProjectStatus

@pytest.fixture
async def sample_project_with_segment(db_session):
    project_id = uuid.uuid4()
    segment_id = uuid.uuid4()
    
    project = Project(
        id=project_id,
        name="Test Edit Project",
        status=ProjectStatus.REVIEW
    )
    doc = Document(
        id=uuid.uuid4(),
        project_id=project_id,
        original_filename="test.pdf",
        file_path="storage/uploads/test.pdf",
        source_language="de"
    )
    page = DocumentPage(
        id=uuid.uuid4(),
        document_id=doc.id,
        number=1,
        width=100.0,
        height=100.0
    )
    segment = DocumentSegment(
        id=segment_id,
        document_id=doc.id,
        text="Der Hochschrank ist kaputt.",
        is_translatable=True,
        translations={"en": "The tall unit is broken."},
        annotations={"en": []},
        issues={"en": []},
        page_number=1,
        order_index=0,
        kind="paragraph",
        bounding_box=[0.0, 0.0, 10.0, 10.0]
    )
    
    db_session.add(project)
    db_session.add(doc)
    db_session.add(page)
    db_session.add(segment)
    await db_session.commit()
    
    return {"project_id": str(project_id), "segment_id": str(segment_id)}

async def test_patch_segment_success(client: AsyncClient, sample_project_with_segment):
    p_id = sample_project_with_segment["project_id"]
    s_id = sample_project_with_segment["segment_id"]
    
    response = await client.patch(
        f"/api/projects/{p_id}/segments/{s_id}",
        json={"target_language": "en", "new_text": "The tall cabinet is broken."}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["translations"]["en"] == "The tall cabinet is broken."

async def test_patch_segment_empty_string_triggers_qa(client: AsyncClient, sample_project_with_segment):
    p_id = sample_project_with_segment["project_id"]
    s_id = sample_project_with_segment["segment_id"]
    
    response = await client.patch(
        f"/api/projects/{p_id}/segments/{s_id}",
        json={"target_language": "en", "new_text": ""}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["translations"]["en"] == ""
    assert any(issue["type"] == "untranslated" for issue in data["issues"]["en"])

async def test_patch_segment_not_found(client: AsyncClient, sample_project_with_segment):
    p_id = sample_project_with_segment["project_id"]
    fake_s_id = str(uuid.uuid4())
    
    response = await client.patch(
        f"/api/projects/{p_id}/segments/{fake_s_id}",
        json={"target_language": "en", "new_text": "Fake"}
    )
    
    assert response.status_code == 404
