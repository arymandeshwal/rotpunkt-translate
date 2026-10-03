import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.languages import LANGUAGES
from app.models import GlossaryCategory, GlossaryEntry, GlossaryTerm


def entry(*terms: tuple[str, str], **fields: object) -> GlossaryEntry:
    return GlossaryEntry(
        terms=[GlossaryTerm(language=lang, text=value) for lang, value in terms], **fields
    )


async def test_entry_with_terms_is_persisted_with_defaults(db_session: AsyncSession) -> None:
    db_session.add(entry(("de", "Hochschrank"), ("en", "tall unit"), ("fr", "armoire haute")))
    await db_session.commit()

    stored = (await db_session.scalars(select(GlossaryEntry))).one()
    assert {t.language: t.text for t in stored.terms} == {
        "de": "Hochschrank",
        "en": "tall unit",
        "fr": "armoire haute",
    }
    assert stored.category is GlossaryCategory.GENERAL
    assert stored.do_not_translate is False
    assert stored.case_sensitive is False
    assert stored.description is None
    assert stored.created_at is not None
    assert stored.updated_at is not None


async def test_all_fields_round_trip(db_session: AsyncSession) -> None:
    db_session.add(
        entry(
            ("de", "Zerox HPL XT"),
            category=GlossaryCategory.PRODUCT_NAME,
            do_not_translate=True,
            case_sensitive=True,
            description="Front programme, high-pressure laminate",
        )
    )
    await db_session.commit()

    stored = (await db_session.scalars(select(GlossaryEntry))).one()
    assert stored.category is GlossaryCategory.PRODUCT_NAME
    assert stored.do_not_translate is True
    assert stored.case_sensitive is True
    assert stored.description == "Front programme, high-pressure laminate"


async def test_every_supported_language_is_accepted(db_session: AsyncSession) -> None:
    """Guards against the DB constraint drifting from app.languages.LANGUAGES."""
    db_session.add(entry(*((code, f"term-{code}") for code in LANGUAGES)))
    await db_session.flush()

    assert await db_session.scalar(select(func.count(GlossaryTerm.id))) == len(LANGUAGES)


async def test_unsupported_language_is_rejected(db_session: AsyncSession) -> None:
    db_session.add(entry(("xx", "Hochschrank")))

    with pytest.raises(IntegrityError, match="ck_glossary_terms_language_supported"):
        await db_session.flush()


@pytest.mark.parametrize("blank", ["", "   "])
async def test_blank_term_is_rejected(db_session: AsyncSession, blank: str) -> None:
    db_session.add(entry(("de", blank)))

    with pytest.raises(IntegrityError, match="ck_glossary_terms_text_not_blank"):
        await db_session.flush()


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("Hochschrank", "Hochschrank"),
        ("Hochschrank", "HOCHSCHRANK"),
        ("Spülunterschrank", "SPÜLUNTERSCHRANK"),  # case folding must cover umlauts
    ],
)
async def test_duplicate_term_in_same_language_is_rejected(
    db_session: AsyncSession, first: str, second: str
) -> None:
    db_session.add(entry(("de", first)))
    await db_session.flush()
    db_session.add(entry(("de", second)))

    with pytest.raises(IntegrityError, match="uq_glossary_terms_language_lower_text"):
        await db_session.flush()


async def test_same_text_in_different_languages_is_allowed(db_session: AsyncSession) -> None:
    # "Front" is both German and English.
    db_session.add(entry(("de", "Front"), ("en", "front")))
    db_session.add(entry(("nl", "front")))
    await db_session.flush()

    assert await db_session.scalar(select(func.count(GlossaryTerm.id))) == 3


async def test_entry_has_at_most_one_term_per_language(db_session: AsyncSession) -> None:
    db_session.add(entry(("de", "Auszug"), ("de", "Schublade")))

    with pytest.raises(IntegrityError, match="uq_glossary_terms_entry_id_language"):
        await db_session.flush()


async def test_unknown_category_is_rejected_by_database(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="ck_glossary_entries_category"):
        await db_session.execute(text("INSERT INTO glossary_entries (category) VALUES ('colour')"))


async def test_deleting_entry_deletes_its_terms(db_session: AsyncSession) -> None:
    hochschrank = entry(("de", "Hochschrank"), ("en", "tall unit"))
    db_session.add_all([hochschrank, entry(("de", "Kochfeld"), ("en", "hob"))])
    await db_session.flush()

    await db_session.delete(hochschrank)
    await db_session.flush()

    remaining = (await db_session.scalars(select(GlossaryTerm.text))).all()
    assert sorted(remaining) == ["Kochfeld", "hob"]


async def test_database_cascades_term_deletion(db_session: AsyncSession) -> None:
    """ON DELETE CASCADE also holds for deletes that bypass the ORM."""
    db_session.add(entry(("de", "Hochschrank"), ("en", "tall unit")))
    await db_session.flush()

    await db_session.execute(text("DELETE FROM glossary_entries"))

    assert await db_session.scalar(select(func.count(GlossaryTerm.id))) == 0


async def test_terms_load_sorted_by_language(db_session: AsyncSession) -> None:
    db_session.add(entry(("nl", "hoge kast"), ("de", "Hochschrank"), ("en", "tall unit")))
    await db_session.commit()
    db_session.expunge_all()

    stored = (await db_session.scalars(select(GlossaryEntry))).one()
    assert [t.language for t in stored.terms] == ["de", "en", "nl"]
