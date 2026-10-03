from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GlossaryCategory, GlossaryEntry
from app.seed import load_glossary_seed, seed_glossary
from tests.factories import add_entry


def test_seed_file_is_valid() -> None:
    entries = load_glossary_seed()

    assert len(entries) > 0
    categories = Counter(e.category for e in entries)
    assert categories[GlossaryCategory.KITCHEN_TERM] > 0
    assert categories[GlossaryCategory.PRODUCT_NAME] > 0


def test_seed_file_has_no_duplicate_terms() -> None:
    seen = Counter(
        (term.language, term.text.lower()) for e in load_glossary_seed() for term in e.terms
    )

    assert [key for key, count in seen.items() if count > 1] == []


def test_product_names_in_seed_are_protected() -> None:
    products = [e for e in load_glossary_seed() if e.category is GlossaryCategory.PRODUCT_NAME]

    assert all(e.do_not_translate for e in products)


async def test_seed_creates_every_entry(db_session: AsyncSession) -> None:
    entries = load_glossary_seed()

    result = await seed_glossary(db_session, entries)

    assert result.created == len(entries)
    assert result.skipped == []
    assert await db_session.scalar(select(func.count(GlossaryEntry.id))) == len(entries)


async def test_seed_is_idempotent(db_session: AsyncSession) -> None:
    entries = load_glossary_seed()
    await seed_glossary(db_session, entries)

    second = await seed_glossary(db_session, entries)

    assert second.created == 0
    assert len(second.skipped) == len(entries)
    assert await db_session.scalar(select(func.count(GlossaryEntry.id))) == len(entries)


async def test_seed_does_not_overwrite_user_edits(db_session: AsyncSession) -> None:
    edited = await add_entry(
        db_session, {"de": "Hochschrank", "en": "tall cabinet"}, description="Our wording"
    )

    result = await seed_glossary(db_session, load_glossary_seed())

    assert "Hochschrank" in result.skipped
    await db_session.refresh(edited)
    assert {t.language: t.text for t in edited.terms} == {"de": "Hochschrank", "en": "tall cabinet"}
    assert edited.description == "Our wording"
