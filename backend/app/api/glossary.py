from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_role
from app.db import get_session
from app.languages import DEFAULT_SOURCE_LANGUAGE, LANGUAGES, LanguageCode
from app.models import GlossaryCategory
from app.models.user import Role, User
from app.schemas.glossary import (
    DuplicateTermsResponse,
    GlossaryEntryCreate,
    GlossaryEntryOut,
    GlossaryEntryUpdate,
    GlossaryPage,
    LanguageOut,
    SortField,
    SortOrder,
)
from app.services import glossary as service

router = APIRouter(tags=["glossary"])

Session = Annotated[AsyncSession, Depends(get_session)]

NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "Glossary entry not found"}}
CONFLICT: dict[int | str, dict[str, Any]] = {
    409: {"model": DuplicateTermsResponse, "description": "A term already exists"}
}


def _not_found(entry_id: int) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"Glossary entry {entry_id} not found")


def _conflict(exc: service.DuplicateTermsError) -> HTTPException:
    detail = {
        "message": str(exc),
        "conflicts": [c.model_dump() for c in exc.conflicts],
    }
    return HTTPException(status.HTTP_409_CONFLICT, detail)


def _invalid(exc: service.InvalidEntryError) -> HTTPException:
    # Same shape as FastAPI's own validation errors, so clients handle both alike.
    detail = [{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}]
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


@router.get("/languages", response_model=list[LanguageOut])
async def list_languages(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[LanguageOut]:
    return [LanguageOut(code=code, name=name) for code, name in LANGUAGES.items()]


@router.get("/glossary", response_model=GlossaryPage)
async def list_glossary_entries(
    session: Session,
    current_user: Annotated[User, Depends(get_current_user)],
    q: Annotated[
        str | None, Query(max_length=255, description="Search terms in all languages")
    ] = None,
    category: GlossaryCategory | None = None,
    do_not_translate: bool | None = None,
    case_sensitive: bool | None = None,
    missing: Annotated[
        LanguageCode | None, Query(description="Only entries without a term in this language")
    ] = None,
    sort: SortField = DEFAULT_SOURCE_LANGUAGE,
    order: SortOrder = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> GlossaryPage:
    filters = service.GlossaryFilters(
        q=q,
        category=category,
        do_not_translate=do_not_translate,
        case_sensitive=case_sensitive,
        missing=missing,
    )
    items, total = await service.list_entries(
        session, filters, sort=sort, order=order, page=page, page_size=page_size
    )
    return GlossaryPage(
        items=[GlossaryEntryOut.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/glossary/{entry_id}", response_model=GlossaryEntryOut, responses=NOT_FOUND)
async def get_glossary_entry(
    entry_id: int, session: Session, current_user: Annotated[User, Depends(get_current_user)]
) -> GlossaryEntryOut:
    try:
        entry = await service.get_entry(session, entry_id)
    except service.EntryNotFoundError:
        raise _not_found(entry_id) from None
    return GlossaryEntryOut.model_validate(entry)


@router.post(
    "/glossary",
    response_model=GlossaryEntryOut,
    status_code=status.HTTP_201_CREATED,
    responses=CONFLICT,
)
async def create_glossary_entry(
    data: GlossaryEntryCreate,
    session: Session,
    current_user: Annotated[
        User, Depends(require_role([Role.ADMIN, Role.REVIEWER, Role.TRANSLATOR]))
    ],
) -> GlossaryEntryOut:
    try:
        entry = await service.create_entry(session, data)
    except service.DuplicateTermsError as exc:
        raise _conflict(exc) from None
    return GlossaryEntryOut.model_validate(entry)


@router.patch(
    "/glossary/{entry_id}",
    response_model=GlossaryEntryOut,
    responses={**NOT_FOUND, **CONFLICT},
)
async def update_glossary_entry(
    entry_id: int,
    data: GlossaryEntryUpdate,
    session: Session,
    current_user: Annotated[
        User, Depends(require_role([Role.ADMIN, Role.REVIEWER, Role.TRANSLATOR]))
    ],
) -> GlossaryEntryOut:
    try:
        entry = await service.update_entry(session, entry_id, data)
    except service.EntryNotFoundError:
        raise _not_found(entry_id) from None
    except service.DuplicateTermsError as exc:
        raise _conflict(exc) from None
    except service.InvalidEntryError as exc:
        raise _invalid(exc) from None
    return GlossaryEntryOut.model_validate(entry)


@router.delete("/glossary/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
async def delete_glossary_entry(
    entry_id: int,
    session: Session,
    current_user: Annotated[User, Depends(require_role([Role.ADMIN, Role.REVIEWER]))],
) -> Response:
    try:
        await service.delete_entry(session, entry_id)
    except service.EntryNotFoundError:
        raise _not_found(entry_id) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
