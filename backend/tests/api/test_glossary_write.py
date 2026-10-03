from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GlossaryCategory
from tests.factories import add_entry


def terms(**by_language: str) -> list[dict[str, str]]:
    return [{"language": lang, "text": value} for lang, value in by_language.items()]


async def create(client: AsyncClient, **body: Any) -> dict[str, Any]:
    response = await client.post("/api/glossary", json=body)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


# --- create -------------------------------------------------------------------------------


async def test_create_entry(client: AsyncClient) -> None:
    body = await create(
        client,
        category="kitchen_term",
        description="Tall cabinet, usually 2 m or more",
        terms=terms(de="Hochschrank", en="tall unit"),
    )

    assert body["category"] == "kitchen_term"
    assert body["description"] == "Tall cabinet, usually 2 m or more"
    assert body["terms"] == terms(de="Hochschrank", en="tall unit")

    fetched = await client.get(f"/api/glossary/{body['id']}")
    assert fetched.json() == body


async def test_create_applies_defaults(client: AsyncClient) -> None:
    body = await create(client, terms=terms(de="Pflegehinweise"))

    assert body["category"] == "general"
    assert body["do_not_translate"] is False
    assert body["case_sensitive"] is False
    assert body["description"] is None


async def test_create_returns_terms_sorted_by_language(client: AsyncClient) -> None:
    body = await create(client, terms=terms(nl="hoge kast", de="Hochschrank", en="tall unit"))

    assert [t["language"] for t in body["terms"]] == ["de", "en", "nl"]


async def test_create_normalizes_whitespace(client: AsyncClient) -> None:
    body = await create(
        client, description="   ", terms=terms(en="  tall \t  unit  ", de="Hochschrank")
    )

    assert body["terms"] == terms(de="Hochschrank", en="tall unit")
    assert body["description"] is None


async def test_create_do_not_translate_entry(client: AsyncClient) -> None:
    body = await create(
        client, category="product_name", do_not_translate=True, terms=terms(de="Zerox HPL XT")
    )

    assert body["do_not_translate"] is True


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({}, "terms"),
        ({"terms": []}, "terms"),
        ({"terms": terms(xx="Hochschrank")}, "terms"),
        ({"terms": terms(de="   ")}, "terms"),
        ({"terms": terms(de="x" * 256)}, "terms"),
        ({"terms": [*terms(de="Auszug"), *terms(de="Schublade")]}, "terms"),
        ({"category": "colour", "terms": terms(de="Hochschrank")}, "category"),
        ({"description": "x" * 2001, "terms": terms(de="Hochschrank")}, "description"),
        ({"do_not_translate": True, "terms": terms(de="FENIX", en="FENIX")}, None),
    ],
    ids=[
        "missing-terms",
        "empty-terms",
        "unknown-language",
        "blank-term",
        "term-too-long",
        "repeated-language",
        "unknown-category",
        "description-too-long",
        "dnt-with-two-terms",
    ],
)
async def test_create_rejects_invalid_input(
    client: AsyncClient, body: dict[str, Any], field: str | None
) -> None:
    response = await client.post("/api/glossary", json=body)

    assert response.status_code == 422
    if field is not None:
        assert field in response.json()["detail"][0]["loc"]


@pytest.mark.parametrize("duplicate", ["Hochschrank", "HOCHSCHRANK", " hochschrank "])
async def test_create_duplicate_term_returns_409_with_conflicts(
    client: AsyncClient, db_session: AsyncSession, duplicate: str
) -> None:
    existing = await add_entry(db_session, {"de": "Hochschrank", "en": "tall unit"})

    response = await client.post(
        "/api/glossary", json={"terms": terms(de=duplicate, en="high cabinet")}
    )

    assert response.status_code == 409
    assert response.json()["detail"]["conflicts"] == [
        {"language": "de", "text": "Hochschrank", "entry_id": existing.id}
    ]


async def test_create_reports_every_conflicting_term(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    first = await add_entry(db_session, {"de": "Hochschrank"})
    second = await add_entry(db_session, {"en": "tall unit"})

    response = await client.post(
        "/api/glossary", json={"terms": terms(de="Hochschrank", en="tall unit")}
    )

    assert response.status_code == 409
    assert response.json()["detail"]["conflicts"] == [
        {"language": "de", "text": "Hochschrank", "entry_id": first.id},
        {"language": "en", "text": "tall unit", "entry_id": second.id},
    ]


async def test_same_text_in_another_language_is_not_a_conflict(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await add_entry(db_session, {"de": "Front"})

    await create(client, terms=terms(en="front"))


# --- update -------------------------------------------------------------------------------


async def test_update_fields_without_touching_terms(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    entry = await add_entry(db_session, {"de": "Hochschrank", "en": "tall unit"})

    response = await client.patch(
        f"/api/glossary/{entry.id}",
        json={"category": "kitchen_term", "case_sensitive": True, "description": "Tall cabinet"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "kitchen_term"
    assert body["case_sensitive"] is True
    assert body["description"] == "Tall cabinet"
    assert body["terms"] == terms(de="Hochschrank", en="tall unit")


async def test_update_replaces_terms_edit_add_and_remove(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    entry = await add_entry(db_session, {"de": "Hochschrank", "en": "high unit", "fr": "colonne"})

    response = await client.patch(
        f"/api/glossary/{entry.id}",
        json={"terms": terms(de="Hochschrank", en="tall unit", nl="hoge kast")},
    )

    assert response.status_code == 200
    assert response.json()["terms"] == terms(de="Hochschrank", en="tall unit", nl="hoge kast")


async def test_update_may_change_casing_of_own_term(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    entry = await add_entry(db_session, {"de": "hochschrank"})

    response = await client.patch(
        f"/api/glossary/{entry.id}", json={"terms": terms(de="Hochschrank")}
    )

    assert response.status_code == 200
    assert response.json()["terms"] == terms(de="Hochschrank")


async def test_update_conflicting_with_another_entry_returns_409_and_changes_nothing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    other = await add_entry(db_session, {"de": "Kochfeld"})
    entry = await add_entry(db_session, {"de": "Hochschrank"})

    response = await client.patch(
        f"/api/glossary/{entry.id}",
        json={"category": "kitchen_term", "terms": terms(de="KOCHFELD")},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["conflicts"][0]["entry_id"] == other.id
    unchanged = (await client.get(f"/api/glossary/{entry.id}")).json()
    assert unchanged["terms"] == terms(de="Hochschrank")
    assert unchanged["category"] == "general"


async def test_update_explicit_null_clears_description(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    entry = await add_entry(db_session, {"de": "Hochschrank"}, description="Tall cabinet")

    kept = await client.patch(f"/api/glossary/{entry.id}", json={"category": "kitchen_term"})
    cleared = await client.patch(f"/api/glossary/{entry.id}", json={"description": None})

    assert kept.json()["description"] == "Tall cabinet"
    assert cleared.json()["description"] is None


async def test_update_with_empty_body_changes_nothing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    entry = await add_entry(db_session, {"de": "Hochschrank"}, category=GlossaryCategory.GENERAL)

    response = await client.patch(f"/api/glossary/{entry.id}", json={})

    assert response.status_code == 200
    assert response.json()["terms"] == terms(de="Hochschrank")


async def test_update_terms_bumps_updated_at(client: AsyncClient, db_session: AsyncSession) -> None:
    entry = await add_entry(db_session, {"de": "Hochschrank"})
    await db_session.execute(
        text("UPDATE glossary_entries SET updated_at = '2020-01-01T00:00:00Z' WHERE id = :id"),
        {"id": entry.id},
    )

    response = await client.patch(
        f"/api/glossary/{entry.id}", json={"terms": terms(de="Hochschrank", en="tall unit")}
    )

    assert not response.json()["updated_at"].startswith("2020-01-01")


async def test_update_rejects_do_not_translate_with_several_terms(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    entry = await add_entry(db_session, {"de": "FENIX", "en": "FENIX"})

    response = await client.patch(f"/api/glossary/{entry.id}", json={"do_not_translate": True})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "terms"]


async def test_update_rejects_second_term_on_do_not_translate_entry(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    entry = await add_entry(db_session, {"de": "FENIX"}, do_not_translate=True)

    response = await client.patch(
        f"/api/glossary/{entry.id}", json={"terms": terms(de="FENIX", en="FENIX")}
    )

    assert response.status_code == 422


async def test_update_can_mark_single_term_entry_do_not_translate(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    entry = await add_entry(db_session, {"de": "FENIX", "en": "FENIX"})

    response = await client.patch(
        f"/api/glossary/{entry.id}",
        json={"do_not_translate": True, "category": "product_name", "terms": terms(de="FENIX")},
    )

    assert response.status_code == 200
    assert response.json()["do_not_translate"] is True
    assert response.json()["terms"] == terms(de="FENIX")


@pytest.mark.parametrize(
    "body",
    [{"terms": []}, {"terms": terms(xx="Hochschrank")}, {"category": "colour"}],
    ids=["empty-terms", "unknown-language", "unknown-category"],
)
async def test_update_rejects_invalid_input(
    client: AsyncClient, db_session: AsyncSession, body: dict[str, Any]
) -> None:
    entry = await add_entry(db_session, {"de": "Hochschrank"})

    response = await client.patch(f"/api/glossary/{entry.id}", json=body)

    assert response.status_code == 422


async def test_update_unknown_entry_returns_404(client: AsyncClient) -> None:
    response = await client.patch("/api/glossary/999999", json={"category": "general"})

    assert response.status_code == 404


# --- delete -------------------------------------------------------------------------------


async def test_delete_entry(client: AsyncClient, db_session: AsyncSession) -> None:
    entry = await add_entry(db_session, {"de": "Hochschrank", "en": "tall unit"})

    response = await client.delete(f"/api/glossary/{entry.id}")

    assert response.status_code == 204
    assert response.content == b""
    assert (await client.get(f"/api/glossary/{entry.id}")).status_code == 404


async def test_deleted_terms_can_be_reused(client: AsyncClient, db_session: AsyncSession) -> None:
    entry = await add_entry(db_session, {"de": "Hochschrank"})
    await client.delete(f"/api/glossary/{entry.id}")

    await create(client, terms=terms(de="Hochschrank"))


async def test_delete_unknown_entry_returns_404(client: AsyncClient) -> None:
    response = await client.delete("/api/glossary/999999")

    assert response.status_code == 404
