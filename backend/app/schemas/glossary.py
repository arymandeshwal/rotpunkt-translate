from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.languages import LanguageCode
from app.models import GlossaryCategory


def _normalize_term(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("Term must not be blank")
    return normalized


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


TermText = Annotated[str, Field(max_length=255), AfterValidator(_normalize_term)]
Description = Annotated[
    Annotated[str, Field(max_length=2000)] | None, AfterValidator(_blank_to_none)
]

SortField = Literal[LanguageCode, "created_at", "updated_at"]
SortOrder = Literal["asc", "desc"]

DNT_SINGLE_TERM_MESSAGE = (
    "A do-not-translate entry must have exactly one term; it is used unchanged in every language"
)


class TermIn(BaseModel):
    language: LanguageCode
    text: TermText


class TermOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: LanguageCode
    text: str


def _check_unique_languages(terms: list[TermIn]) -> list[TermIn]:
    languages = [t.language for t in terms]
    duplicates = sorted({lang for lang in languages if languages.count(lang) > 1})
    if duplicates:
        raise ValueError(f"Only one term per language allowed; repeated: {', '.join(duplicates)}")
    return terms


TermList = Annotated[list[TermIn], Field(min_length=1), AfterValidator(_check_unique_languages)]


class GlossaryEntryCreate(BaseModel):
    category: GlossaryCategory = GlossaryCategory.GENERAL
    do_not_translate: bool = False
    case_sensitive: bool = False
    description: Description = None
    terms: TermList

    @model_validator(mode="after")
    def _dnt_has_single_term(self) -> Self:
        if self.do_not_translate and len(self.terms) != 1:
            raise ValueError(DNT_SINGLE_TERM_MESSAGE)
        return self


class GlossaryEntryUpdate(BaseModel):
    """Partial update. `terms`, when given, replaces the entry's full set of terms."""

    category: GlossaryCategory | None = None
    do_not_translate: bool | None = None
    case_sensitive: bool | None = None
    description: Description = None
    terms: TermList | None = None


class GlossaryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: GlossaryCategory
    do_not_translate: bool
    case_sensitive: bool
    description: str | None
    terms: list[TermOut]
    created_at: datetime
    updated_at: datetime


class GlossaryPage(BaseModel):
    items: list[GlossaryEntryOut]
    total: int
    page: int
    page_size: int


class TermConflict(BaseModel):
    language: LanguageCode
    text: str
    entry_id: int


class DuplicateTermsDetail(BaseModel):
    message: str
    conflicts: list[TermConflict]


class DuplicateTermsResponse(BaseModel):
    detail: DuplicateTermsDetail


class LanguageOut(BaseModel):
    code: LanguageCode
    name: str
