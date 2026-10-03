from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GlossaryCategory, GlossaryEntry, GlossaryTerm


async def add_entry(
    session: AsyncSession,
    terms: dict[str, str],
    *,
    category: GlossaryCategory = GlossaryCategory.GENERAL,
    do_not_translate: bool = False,
    **fields: Any,
) -> GlossaryEntry:
    """Insert a glossary entry directly, bypassing the API."""
    entry = GlossaryEntry(
        category=category,
        do_not_translate=do_not_translate,
        terms=[GlossaryTerm(language=lang, text=text) for lang, text in terms.items()],
        **fields,
    )
    session.add(entry)
    await session.flush()
    return entry
