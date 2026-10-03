"""create glossary tables

Revision ID: 508ffd824d5d
Revises:
Create Date: 2026-10-03 15:49:39.345941

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "508ffd824d5d"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "glossary_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "kitchen_term",
                "product_name",
                "general",
                name="category",
                native_enum=False,
                create_constraint=False,
                length=32,
            ),
            server_default="general",
            nullable=False,
        ),
        sa.Column(
            "do_not_translate", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("case_sensitive", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('kitchen_term', 'product_name', 'general')",
            name=op.f("ck_glossary_entries_category"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_glossary_entries")),
    )
    op.create_table(
        "glossary_terms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("text", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "language IN ('de', 'en', 'fr', 'nl', 'da', 'nb', 'es')",
            name=op.f("ck_glossary_terms_language_supported"),
        ),
        sa.CheckConstraint(
            "length(btrim(text)) > 0", name=op.f("ck_glossary_terms_text_not_blank")
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["glossary_entries.id"],
            name=op.f("fk_glossary_terms_entry_id_glossary_entries"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_glossary_terms")),
        sa.UniqueConstraint(
            "entry_id", "language", name=op.f("uq_glossary_terms_entry_id_language")
        ),
    )
    op.create_index(
        op.f("ix_glossary_terms_entry_id"), "glossary_terms", ["entry_id"], unique=False
    )
    op.create_index(
        "uq_glossary_terms_language_lower_text",
        "glossary_terms",
        ["language", sa.literal_column("lower(text)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_glossary_terms_language_lower_text", table_name="glossary_terms")
    op.drop_index(op.f("ix_glossary_terms_entry_id"), table_name="glossary_terms")
    op.drop_table("glossary_terms")
    op.drop_table("glossary_entries")
