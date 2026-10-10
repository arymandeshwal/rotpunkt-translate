"""Import every model here so Base.metadata is complete for Alembic."""

from app.models.glossary import GlossaryCategory, GlossaryEntry, GlossaryTerm
from app.models.project import Document, DocumentPage, DocumentSegment, Project, ProjectStatus
from app.models.user import Role, User

__all__ = [
    "GlossaryCategory",
    "GlossaryEntry",
    "GlossaryTerm",
    "Project",
    "ProjectStatus",
    "Document",
    "DocumentPage",
    "DocumentSegment",
    "User",
    "Role",
]
