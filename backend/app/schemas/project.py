import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.languages import LanguageCode
from app.models.project import ProjectStatus


class DocumentPageSchema(BaseModel):
    id: uuid.UUID
    number: int
    width: float
    height: float
    warnings: list[str]

    model_config = ConfigDict(from_attributes=True)


class SegmentCommentCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Comment text")


class SegmentCommentAuthor(BaseModel):
    id: uuid.UUID
    email: str

    model_config = ConfigDict(from_attributes=True)


class SegmentCommentResponse(BaseModel):
    id: uuid.UUID
    segment_id: uuid.UUID
    user_id: uuid.UUID
    text: str
    created_at: datetime
    updated_at: datetime
    user: SegmentCommentAuthor | None = None

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
    translations: dict[str, str]
    annotations: dict[str, list[dict]] = Field(default_factory=dict)
    issues: dict[str, list[dict]] = Field(default_factory=dict)
    comments: list[SegmentCommentResponse] = Field(default_factory=list)

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


class TranslateRequest(BaseModel):
    target_language: LanguageCode


class SegmentEditRequest(BaseModel):
    target_language: LanguageCode
    new_text: str


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    documents: list[DocumentSchema]

    model_config = ConfigDict(from_attributes=True)
