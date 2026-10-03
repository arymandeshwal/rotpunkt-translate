from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin
from app.languages import LANGUAGES


class GlossaryCategory(StrEnum):
    KITCHEN_TERM = "kitchen_term"
    PRODUCT_NAME = "product_name"
    GENERAL = "general"


class GlossaryEntry(TimestampMixin, Base):
    """One concept, e.g. "tall unit", with one term per language."""

    __tablename__ = "glossary_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[GlossaryCategory] = mapped_column(
        Enum(
            GlossaryCategory,
            name="category",
            native_enum=False,
            create_constraint=True,
            length=32,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=GlossaryCategory.GENERAL,
        server_default=GlossaryCategory.GENERAL.value,
    )
    # Term is identical in every language (product names, brands).
    do_not_translate: Mapped[bool] = mapped_column(default=False, server_default=false())
    # Match only the exact casing, e.g. item codes. Uniqueness stays case-insensitive.
    case_sensitive: Mapped[bool] = mapped_column(default=False, server_default=false())
    description: Mapped[str | None] = mapped_column(Text)
    # User id once authentication (M1) exists; no foreign key until the users table does.
    created_by: Mapped[int | None]

    terms: Mapped[list["GlossaryTerm"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by="GlossaryTerm.language",
    )


class GlossaryTerm(Base):
    """The wording of a glossary entry in one language."""

    __tablename__ = "glossary_terms"
    __table_args__ = (
        UniqueConstraint("entry_id", "language"),
        CheckConstraint(
            "language IN (" + ", ".join(f"'{code}'" for code in LANGUAGES) + ")",
            name="language_supported",
        ),
        CheckConstraint("length(btrim(text)) > 0", name="text_not_blank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("glossary_entries.id", ondelete="CASCADE"), index=True
    )
    language: Mapped[str] = mapped_column(String(8))
    text: Mapped[str] = mapped_column(String(255))

    entry: Mapped[GlossaryEntry] = relationship(back_populates="terms")


# A term may exist only once per language, ignoring case ("Hochschrank" == "HOCHSCHRANK").
Index(
    "uq_glossary_terms_language_lower_text",
    GlossaryTerm.language,
    func.lower(GlossaryTerm.text),
    unique=True,
)
