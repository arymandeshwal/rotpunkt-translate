from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.languages import LanguageCode
from app.models import GlossaryCategory, GlossaryEntry, GlossaryTerm
from app.schemas.glossary import (
    DNT_SINGLE_TERM_MESSAGE,
    GlossaryEntryCreate,
    GlossaryEntryUpdate,
    SortField,
    SortOrder,
    TermConflict,
    TermIn,
)

EntrySelect = Select[GlossaryEntry]


class EntryNotFoundError(Exception):
    pass


class DuplicateTermsError(Exception):
    def __init__(self, conflicts: list[TermConflict]) -> None:
        super().__init__("One or more terms already exist in the glossary")
        self.conflicts = conflicts


class InvalidEntryError(Exception):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


@dataclass(frozen=True)
class GlossaryFilters:
    q: str | None = None
    category: GlossaryCategory | None = None
    do_not_translate: bool | None = None
    missing: LanguageCode | None = None


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_filters(stmt: EntrySelect, f: GlossaryFilters) -> EntrySelect:
    if f.q and f.q.strip():
        pattern = f"%{_escape_like(f.q.strip())}%"
        stmt = stmt.where(GlossaryEntry.terms.any(GlossaryTerm.text.ilike(pattern, escape="\\")))
    if f.category is not None:
        stmt = stmt.where(GlossaryEntry.category == f.category)
    if f.do_not_translate is not None:
        stmt = stmt.where(GlossaryEntry.do_not_translate.is_(f.do_not_translate))
    if f.missing is not None:
        # Do-not-translate entries are never "missing" a translation.
        stmt = stmt.where(
            GlossaryEntry.do_not_translate.is_(False),
            ~GlossaryEntry.terms.any(GlossaryTerm.language == f.missing),
        )
    return stmt


def _sort_key(stmt: EntrySelect, sort: SortField) -> tuple[EntrySelect, ColumnElement[Any]]:
    if sort == "created_at":
        return stmt, GlossaryEntry.created_at.expression
    if sort == "updated_at":
        return stmt, GlossaryEntry.updated_at.expression
    # Sort by the term in the chosen language. Do-not-translate entries have a single term
    # that applies to every language, so they sort by that term instead of trailing.
    term = aliased(GlossaryTerm)
    stmt = stmt.outerjoin(term, and_(term.entry_id == GlossaryEntry.id, term.language == sort))
    only_term = (
        select(func.min(GlossaryTerm.text))
        .where(GlossaryTerm.entry_id == GlossaryEntry.id)
        .correlate(GlossaryEntry)
        .scalar_subquery()
    )
    fallback = case((GlossaryEntry.do_not_translate, only_term), else_=None)
    return stmt, func.lower(func.coalesce(term.text, fallback))


async def list_entries(
    session: AsyncSession,
    filters: GlossaryFilters,
    *,
    sort: SortField,
    order: SortOrder,
    page: int,
    page_size: int,
) -> tuple[Sequence[GlossaryEntry], int]:
    filtered = _apply_filters(select(GlossaryEntry), filters)
    total = await session.scalar(select(func.count()).select_from(filtered.subquery())) or 0

    stmt, key = _sort_key(filtered, sort)
    direction = key.asc() if order == "asc" else key.desc()
    stmt = (
        stmt.order_by(direction.nulls_last(), GlossaryEntry.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await session.scalars(stmt)).all()
    return items, total


async def get_entry(session: AsyncSession, entry_id: int) -> GlossaryEntry:
    stmt = (
        select(GlossaryEntry)
        .where(GlossaryEntry.id == entry_id)
        .execution_options(populate_existing=True)
    )
    entry = await session.scalar(stmt)
    if entry is None:
        raise EntryNotFoundError(entry_id)
    return entry


async def _find_conflicts(
    session: AsyncSession, terms: Sequence[TermIn], exclude_entry_id: int | None
) -> list[TermConflict]:
    matches = [
        and_(
            GlossaryTerm.language == t.language, func.lower(GlossaryTerm.text) == func.lower(t.text)
        )
        for t in terms
    ]
    stmt = select(GlossaryTerm).where(or_(*matches))
    if exclude_entry_id is not None:
        stmt = stmt.where(GlossaryTerm.entry_id != exclude_entry_id)
    existing = (await session.scalars(stmt.order_by(GlossaryTerm.language))).all()
    return [TermConflict(language=t.language, text=t.text, entry_id=t.entry_id) for t in existing]


async def _commit(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        # A concurrent request inserted the same term between our check and the commit.
        await session.rollback()
        if "uq_glossary_terms_language_lower_text" in str(exc.orig):
            raise DuplicateTermsError([]) from exc
        raise


async def create_entry(session: AsyncSession, data: GlossaryEntryCreate) -> GlossaryEntry:
    conflicts = await _find_conflicts(session, data.terms, exclude_entry_id=None)
    if conflicts:
        raise DuplicateTermsError(conflicts)

    entry = GlossaryEntry(
        category=data.category,
        do_not_translate=data.do_not_translate,
        case_sensitive=data.case_sensitive,
        description=data.description,
        terms=[GlossaryTerm(language=t.language, text=t.text) for t in data.terms],
    )
    session.add(entry)
    await _commit(session)
    return await get_entry(session, entry.id)


def _replace_terms(entry: GlossaryEntry, terms: Sequence[TermIn]) -> None:
    # Update in place rather than delete + insert: the unit of work inserts before it deletes,
    # which would trip the one-term-per-language constraint.
    incoming = {t.language: t.text for t in terms}
    for term in list(entry.terms):
        if term.language in incoming:
            term.text = incoming.pop(term.language)
        else:
            entry.terms.remove(term)
    entry.terms.extend(GlossaryTerm(language=lang, text=text) for lang, text in incoming.items())


async def update_entry(
    session: AsyncSession, entry_id: int, data: GlossaryEntryUpdate
) -> GlossaryEntry:
    entry = await get_entry(session, entry_id)
    changes = data.model_fields_set

    do_not_translate = (
        data.do_not_translate if data.do_not_translate is not None else entry.do_not_translate
    )
    term_count = len(data.terms) if data.terms is not None else len(entry.terms)
    if do_not_translate and term_count != 1:
        raise InvalidEntryError("terms", DNT_SINGLE_TERM_MESSAGE)

    if data.terms is not None:
        conflicts = await _find_conflicts(session, data.terms, exclude_entry_id=entry.id)
        if conflicts:
            raise DuplicateTermsError(conflicts)
        _replace_terms(entry, data.terms)

    if data.category is not None:
        entry.category = data.category
    if data.do_not_translate is not None:
        entry.do_not_translate = data.do_not_translate
    if data.case_sensitive is not None:
        entry.case_sensitive = data.case_sensitive
    if "description" in changes:  # an explicit null clears the description
        entry.description = data.description

    # Term-only edits don't touch the entry row, so bump the timestamp explicitly.
    entry.updated_at = func.now()
    await _commit(session)
    return await get_entry(session, entry.id)


async def delete_entry(session: AsyncSession, entry_id: int) -> None:
    entry = await get_entry(session, entry_id)
    await session.delete(entry)
    await session.commit()
