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
    # Depending on Lingua, this might be 'en', but it definitely shouldn't be 'de'
    # and since the source language is 'de', it should be flagged as not translatable
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
