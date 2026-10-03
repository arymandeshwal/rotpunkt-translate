"""Import every model here so Base.metadata is complete for Alembic."""

from app.models.glossary import GlossaryCategory, GlossaryEntry, GlossaryTerm

__all__ = ["GlossaryCategory", "GlossaryEntry", "GlossaryTerm"]
