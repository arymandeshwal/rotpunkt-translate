import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.languages import LanguageCode
from app.models.project import ProjectStatus


class DocumentPageSchema(BaseModel):
    id: uuid.UUID
    number: int
    width: float
    height: float
    warnings: list[str]

    model_config = ConfigDict(from_attributes=True)


class DocumentSegmentSchema(BaseModel):
    id: uuid.UUID
    page_number: int
    order_index: int
    kind: str
    text: str
    bounding_box: list[float]
    detected_language: str | None
    is_translatable: bool | None

    model_config = ConfigDict(from_attributes=True)


class DocumentSchema(BaseModel):
    id: uuid.UUID
    original_filename: str
    source_language: LanguageCode | None
    
    pages: list[DocumentPageSchema]
    segments: list[DocumentSegmentSchema]

    model_config = ConfigDict(from_attributes=True)


class ProjectUpdateRequest(BaseModel):
    source_language: LanguageCode


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    
    documents: list[DocumentSchema]

    model_config = ConfigDict(from_attributes=True)
