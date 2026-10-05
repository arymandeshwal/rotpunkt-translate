"""Import every model here so Base.metadata is complete for Alembic."""

from app.models.glossary import GlossaryCategory, GlossaryEntry, GlossaryTerm
from app.models.project import Document, DocumentPage, DocumentSegment, Project, ProjectStatus

__all__ = [
    "GlossaryCategory",
    "GlossaryEntry",
    "GlossaryTerm",
    "Project",
    "ProjectStatus",
    "Document",
    "DocumentPage",
    "DocumentSegment",
]
