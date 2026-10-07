import uuid
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin
from app.languages import LanguageCode


class ProjectStatus(StrEnum):
    NEW = "new"
    TRANSLATING = "translating"
    REVIEW = "review"
    DONE = "done"


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(
            ProjectStatus,
            name="project_status",
            native_enum=False,
            length=32,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=ProjectStatus.NEW,
        server_default=ProjectStatus.NEW.value,
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(1024))
    source_language: Mapped[LanguageCode | None] = mapped_column(String(8))

    project: Mapped[Project] = relationship(back_populates="documents")
    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by="DocumentPage.number",
    )
    segments: Mapped[list["DocumentSegment"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by="DocumentSegment.order_index",
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    width: Mapped[float]
    height: Mapped[float]
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")

    document: Mapped[Document] = relationship(back_populates="pages")


class DocumentSegment(Base):
    __tablename__ = "document_segments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer)
    order_index: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32))
    text: Mapped[str]
    bounding_box: Mapped[list[float]] = mapped_column(JSON)
    detected_language: Mapped[str | None] = mapped_column(String(8))
    is_translatable: Mapped[bool | None] = mapped_column(Boolean)
    translations: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, server_default="{}")
    annotations: Mapped[dict[str, list[dict]]] = mapped_column(
        JSON, default=dict, server_default="{}"
    )

    document: Mapped[Document] = relationship(back_populates="segments")
