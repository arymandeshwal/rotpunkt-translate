"""End-to-end tests ensuring the upload API correctly processes the real Rotpunkt sample PDFs.

These tests are skipped if the sample PDFs have not been downloaded (see samples/SOURCES.md).
"""

from pathlib import Path
import pytest
from httpx import AsyncClient

from app.models.project import ProjectStatus
from tests.samples.test_rotpunkt_samples import (
    SAMPLES,
    HPL,
    CHECKLIST,
    DRAWER,
    CATALOG,
)

pytestmark = pytest.mark.skipif(
    not (SAMPLES / HPL).exists(), reason="sample PDFs not downloaded (samples/fetch_samples.py)"
)

@pytest.mark.asyncio
async def test_e2e_upload_hpl_care_instructions(client: AsyncClient) -> None:
    # 1. Upload the real PDF
    pdf_bytes = (SAMPLES / HPL).read_bytes()
    response = await client.post(
        "/api/projects",
        files={"file": (HPL, pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 201
    project = response.json()
    
    # 2. Verify Database Output
    assert project["name"] == Path(HPL).stem
    assert project["status"] == ProjectStatus.NEW.value
    
    doc = project["documents"][0]
    assert doc["original_filename"] == HPL
    
    # The HPL document produces 11 pages (due to PyMuPDF's internal pagination of this specific file)
    assert len(doc["pages"]) == 11
    
    # Verify segments exist and were correctly parsed
    # The exact number can vary slightly based on layout parser tuning, but should be > 50
    assert len(doc["segments"]) > 50 
    
    # 3. Spot check language detection on a mixed document
    # The HPL document has German, English, French, etc.
    # By default, source_language is 'de'.
    # Pure German segments should be translatable
    german_segments = [s for s in doc["segments"] if s["detected_language"] == "de"]
    assert len(german_segments) > 0
    assert all(s["is_translatable"] for s in german_segments)
    
    # Pure French/English segments should be safely flagged False
    foreign_segments = [s for s in doc["segments"] if s["detected_language"] in ("en", "fr")]
    assert len(foreign_segments) > 0
    # There might be some low-confidence or mixed strings, but the majority of
    # high-confidence pure foreign paragraphs should be blocked.
    blocked_foreign = [s for s in foreign_segments if not s["is_translatable"]]
    assert len(blocked_foreign) > 0


@pytest.mark.asyncio
async def test_e2e_upload_checklist_de(client: AsyncClient) -> None:
    filename = CHECKLIST.format("DE")
    pdf_bytes = (SAMPLES / filename).read_bytes()
    response = await client.post(
        "/api/projects",
        files={"file": (filename, pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 201
    doc = response.json()["documents"][0]
    
    # The DE checklist produces 12 pages
    assert len(doc["pages"]) == 12
    
    # Welcome home is their English slogan printed on the last page.
    blocked_segments = [s for s in doc["segments"] if not s["is_translatable"]]
    assert len(blocked_segments) <= 2


@pytest.mark.asyncio
async def test_e2e_upload_massive_catalog(client: AsyncClient) -> None:
    # 1. Upload the real PDF
    pdf_bytes = (SAMPLES / CATALOG).read_bytes()
    response = await client.post(
        "/api/projects",
        files={"file": (CATALOG, pdf_bytes, "application/pdf")}
    )
    
    # 2. Verify it handles large files correctly
    # The catalog produces 17 pages (due to how it is structured internally)
    # We just need to ensure the upload/parse/db cycle succeeds without timing out or crashing.
    assert response.status_code == 201
    doc = response.json()["documents"][0]
    
    assert len(doc["pages"]) == 17
    assert len(doc["segments"]) > 100
