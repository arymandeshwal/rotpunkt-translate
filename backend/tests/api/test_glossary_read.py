from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GlossaryCategory
from tests.factories import add_entry

KITCHEN = GlossaryCategory.KITCHEN_TERM
PRODUCT = GlossaryCategory.PRODUCT_NAME


@pytest.fixture
async def sample(db_session: AsyncSession) -> None:
    await add_entry(
        db_session,
        {"de": "Hochschrank", "en": "tall unit", "fr": "armoire haute"},
        category=KITCHEN,
    )
    await add_entry(
        db_session,
        {"de": "Apothekerhochschrank", "en": "tall apothecary unit"},
        category=KITCHEN,
    )
    await add_entry(db_session, {"de": "arbeitsplatte", "en": "worktop"}, category=KITCHEN)
    await add_entry(db_session, {"de": "Spülunterschrank"}, category=KITCHEN)
    await add_entry(db_session, {"de": "Pflegehinweise", "en": "care instructions"})
    await add_entry(db_session, {"de": "Zerox HPL XT"}, category=PRODUCT, do_not_translate=True)


async def list_glossary(client: AsyncClient, **params: Any) -> dict[str, Any]:
    response = await client.get("/api/glossary", params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def first_terms(body: dict[str, Any], language: str = "de") -> list[str | None]:
    return [
        next((t["text"] for t in item["terms"] if t["language"] == language), None)
        for item in body["items"]
    ]


async def test_languages_endpoint_lists_supported_languages(client: AsyncClient) -> None:
    response = await client.get("/api/languages")

    assert response.status_code == 200
    assert [lang["code"] for lang in response.json()] == ["de", "en", "fr", "nl", "da", "nb", "es"]
    assert response.json()[0] == {"code": "de", "name": "German"}


async def test_empty_glossary(client: AsyncClient) -> None:
    body = await list_glossary(client)

    assert body == {"items": [], "total": 0, "page": 1, "page_size": 50}


@pytest.mark.usefixtures("sample")
async def test_entry_shape(client: AsyncClient) -> None:
    body = await list_glossary(client, q="Hochschrank", sort="en")
    item = next(i for i in body["items"] if i["terms"][0]["text"] == "Hochschrank")

    assert item["category"] == "kitchen_term"
    assert item["do_not_translate"] is False
    assert item["case_sensitive"] is False
    assert item["description"] is None
    assert item["terms"] == [
        {"language": "de", "text": "Hochschrank"},
        {"language": "en", "text": "tall unit"},
        {"language": "fr", "text": "armoire haute"},
    ]
    assert {"id", "created_at", "updated_at"} <= item.keys()


# --- sorting ------------------------------------------------------------------------------


@pytest.mark.usefixtures("sample")
async def test_default_sort_is_german_term_case_insensitive(client: AsyncClient) -> None:
    body = await list_glossary(client)

    assert first_terms(body) == [
        "Apothekerhochschrank",
        "arbeitsplatte",
        "Hochschrank",
        "Pflegehinweise",
        "Spülunterschrank",
        "Zerox HPL XT",
    ]


@pytest.mark.usefixtures("sample")
async def test_sort_descending(client: AsyncClient) -> None:
    body = await list_glossary(client, order="desc")

    assert first_terms(body)[0] == "Zerox HPL XT"
    assert first_terms(body)[-1] == "Apothekerhochschrank"


@pytest.mark.usefixtures("sample")
async def test_sort_by_other_language_puts_missing_terms_last(client: AsyncClient) -> None:
    body = await list_glossary(client, sort="en")

    # Zerox is do-not-translate, so it sorts by its single term among the English terms.
    assert first_terms(body, "de") == [
        "Pflegehinweise",  # care instructions
        "Apothekerhochschrank",  # tall apothecary unit
        "Hochschrank",  # tall unit
        "arbeitsplatte",  # worktop
        "Zerox HPL XT",
        "Spülunterschrank",  # no English term
    ]


@pytest.mark.usefixtures("sample")
async def test_sort_by_created_at(client: AsyncClient) -> None:
    body = await list_glossary(client, sort="created_at")

    assert body["total"] == 6


# --- search -------------------------------------------------------------------------------


@pytest.mark.usefixtures("sample")
async def test_search_matches_substring_case_insensitively(client: AsyncClient) -> None:
    body = await list_glossary(client, q="HOCH")

    assert first_terms(body) == ["Apothekerhochschrank", "Hochschrank"]
    assert body["total"] == 2


@pytest.mark.usefixtures("sample")
async def test_search_matches_any_language_and_returns_all_terms(client: AsyncClient) -> None:
    body = await list_glossary(client, q="armoire")

    assert body["total"] == 1
    assert len(body["items"][0]["terms"]) == 3


@pytest.mark.usefixtures("sample")
async def test_search_handles_umlauts(client: AsyncClient) -> None:
    body = await list_glossary(client, q="SPÜL")

    assert first_terms(body) == ["Spülunterschrank"]


@pytest.mark.usefixtures("sample")
@pytest.mark.parametrize("wildcard", ["%", "_", "\\"])
async def test_search_treats_sql_wildcards_literally(client: AsyncClient, wildcard: str) -> None:
    body = await list_glossary(client, q=wildcard)

    assert body["total"] == 0


@pytest.mark.usefixtures("sample")
async def test_blank_search_returns_everything(client: AsyncClient) -> None:
    body = await list_glossary(client, q="   ")

    assert body["total"] == 6


# --- filters ------------------------------------------------------------------------------


@pytest.mark.usefixtures("sample")
async def test_filter_by_category(client: AsyncClient) -> None:
    body = await list_glossary(client, category="product_name")

    assert first_terms(body) == ["Zerox HPL XT"]


@pytest.mark.usefixtures("sample")
async def test_filter_by_do_not_translate(client: AsyncClient) -> None:
    protected = await list_glossary(client, do_not_translate=True)
    regular = await list_glossary(client, do_not_translate=False)

    assert first_terms(protected) == ["Zerox HPL XT"]
    assert regular["total"] == 5


@pytest.mark.usefixtures("sample")
async def test_filter_missing_language_excludes_do_not_translate(client: AsyncClient) -> None:
    body = await list_glossary(client, missing="en")

    assert first_terms(body) == ["Spülunterschrank"]


@pytest.mark.usefixtures("sample")
async def test_filters_combine(client: AsyncClient) -> None:
    body = await list_glossary(client, q="hoch", category="kitchen_term", missing="fr")

    assert first_terms(body) == ["Apothekerhochschrank"]


# --- pagination ---------------------------------------------------------------------------


@pytest.mark.usefixtures("sample")
async def test_pagination(client: AsyncClient) -> None:
    page2 = await list_glossary(client, page=2, page_size=2)

    assert first_terms(page2) == ["Hochschrank", "Pflegehinweise"]
    assert page2["total"] == 6
    assert (page2["page"], page2["page_size"]) == (2, 2)


@pytest.mark.usefixtures("sample")
async def test_page_past_the_end_is_empty(client: AsyncClient) -> None:
    body = await list_glossary(client, page=99)

    assert body["items"] == []
    assert body["total"] == 6


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 0},
        {"page_size": 101},
        {"missing": "xx"},
        {"sort": "text"},
        {"order": "up"},
        {"category": "colour"},
    ],
)
async def test_invalid_query_parameters_are_rejected(
    client: AsyncClient, params: dict[str, Any]
) -> None:
    response = await client.get("/api/glossary", params=params)

    assert response.status_code == 422


# --- single entry -------------------------------------------------------------------------


async def test_get_entry_by_id(client: AsyncClient, db_session: AsyncSession) -> None:
    entry = await add_entry(db_session, {"de": "Kochfeld", "en": "hob"})

    response = await client.get(f"/api/glossary/{entry.id}")

    assert response.status_code == 200
    assert response.json()["terms"] == [
        {"language": "de", "text": "Kochfeld"},
        {"language": "en", "text": "hob"},
    ]


async def test_get_unknown_entry_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/glossary/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Glossary entry 999999 not found"}
