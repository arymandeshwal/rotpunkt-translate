import uuid
import pytest
from httpx import AsyncClient

from app.models.project import ProjectStatus
from tests.pdf_factory import Text, make_pdf


@pytest.mark.asyncio
async def test_upload_project_success(client: AsyncClient) -> None:
    # 1. Create a dummy PDF
    pdf_content = make_pdf([
        Text("Rotpunkt Küchen Flyer", x=10, y=10, size=24),
        Text("Hochschränke und Unterschränke", x=10, y=100, size=12),
        Text("Please note the new assembly instructions.", x=10, y=200, size=12),
    ])
    
    # 2. Upload it
    response = await client.post(
        "/api/projects",
        files={"file": ("test_flyer.pdf", pdf_content, "application/pdf")}
    )
    
    # 3. Assertions
    assert response.status_code == 201, response.text
    data = response.json()
    
    assert data["name"] == "test_flyer"
    assert data["status"] == ProjectStatus.NEW.value
    assert len(data["documents"]) == 1
    
    doc = data["documents"][0]
    assert doc["original_filename"] == "test_flyer.pdf"
    assert doc["source_language"] == "de"
    
    assert len(doc["pages"]) == 1
    assert len(doc["segments"]) == 3
    
    # Check language detection results
    seg1, seg2, seg3 = doc["segments"]
    assert seg1["text"] == "Rotpunkt Küchen Flyer"
    assert seg1["is_translatable"] is True
    
    assert seg2["text"] == "Hochschränke und Unterschränke"
    assert seg2["detected_language"] == "de"
    assert seg2["is_translatable"] is True
    
    assert seg3["text"] == "Please note the new assembly instructions."
    assert seg3["detected_language"] == "en"
    assert seg3["is_translatable"] is False


@pytest.mark.asyncio
async def test_upload_project_invalid_pdf(client: AsyncClient) -> None:
    response = await client.post(
        "/api/projects",
        files={"file": ("bad.pdf", b"not a pdf", "application/pdf")}
    )
    assert response.status_code == 400
    assert "not a PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient) -> None:
    pdf_content = make_pdf([Text("Test Project", x=10, y=10, size=12)])
    upload_res = await client.post(
        "/api/projects",
        files={"file": ("get_test.pdf", pdf_content, "application/pdf")}
    )
    assert upload_res.status_code == 201
    project_id = upload_res.json()["id"]
    
    get_res = await client.get(f"/api/projects/{project_id}")
    assert get_res.status_code == 200
    
    data = get_res.json()
    assert data["id"] == project_id
    assert data["name"] == "get_test"
    assert len(data["documents"]) == 1
    assert data["documents"][0]["original_filename"] == "get_test.pdf"


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient) -> None:
    random_uuid = str(uuid.uuid4())
    response = await client.get(f"/api/projects/{random_uuid}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_project_source_language(client: AsyncClient) -> None:
    # Upload a mixed PDF
    pdf_content = make_pdf([
        Text("Hochschränke und Unterschränke", x=10, y=100, size=12),
        Text("Please note the new assembly instructions.", x=10, y=200, size=12),
    ])
    upload_res = await client.post(
        "/api/projects",
        files={"file": ("patch_test.pdf", pdf_content, "application/pdf")}
    )
    assert upload_res.status_code == 201
    project_id = upload_res.json()["id"]
    
    # 1. Verify default (de) behavior
    doc = upload_res.json()["documents"][0]
    assert doc["source_language"] == "de"
    seg_de, seg_en = doc["segments"]
    assert seg_de["is_translatable"] is True  # German matches "de"
    assert seg_en["is_translatable"] is False # English blocked by "de"
    
    # 2. Patch the project to English ("en")
    patch_res = await client.patch(
        f"/api/projects/{project_id}",
        json={"source_language": "en"}
    )
    assert patch_res.status_code == 200
    
    # 3. Verify changes were applied and recalculated
    updated_doc = patch_res.json()["documents"][0]
    assert updated_doc["source_language"] == "en"
    
    updated_seg_de, updated_seg_en = updated_doc["segments"]
    
    # Since the source is now English, the pure German sentence should be blocked!
    assert updated_seg_de["is_translatable"] is False
    
    # And the pure English sentence should now be translated!
    assert updated_seg_en["is_translatable"] is True


@pytest.mark.asyncio
async def test_patch_project_not_found(client: AsyncClient) -> None:
    random_uuid = str(uuid.uuid4())
    response = await client.patch(
        f"/api/projects/{random_uuid}",
        json={"source_language": "en"}
    )
    assert response.status_code == 404
