"""Regression tests on Rotpunkt's public sample PDFs.

The expected results were verified by hand. The PDFs are not committed (copyright); fetch
them with `python samples/fetch_samples.py`. Without them these tests are skipped.
"""

from pathlib import Path

import pytest

from app.parsers.pdf import Segment, parse_pdf

SAMPLES = Path(__file__).resolve().parents[3] / "samples" / "downloads"
HPL = "HPL_XTreme.pdf"
CHECKLIST = "Checkliste_Rotpunkt_Kuechen_{}.pdf"
DRAWER = "230315_RP_Flyer_Drawer_Solutions_148x210_AB_RZ_Ansicht.pdf"
CATALOG = "less_is_more-2023.pdf"

pytestmark = pytest.mark.skipif(
    not (SAMPLES / HPL).exists(), reason="sample PDFs not downloaded (samples/fetch_samples.py)"
)

_cache: dict[str, list[Segment]] = {}


def segments(name: str) -> list[Segment]:
    """Parse a sample PDF once per test session.

    Args:
        name: File name inside samples/downloads.

    Returns:
        The document's segments in reading order.
    """
    if name not in _cache:
        _cache[name] = parse_pdf((SAMPLES / name).read_bytes()).segments
    return _cache[name]


def plain(text: str) -> str:
    """Replace thin spaces, which Rotpunkt uses around dashes, with normal spaces.

    Args:
        text: Segment text.

    Returns:
        The text with U+2009 replaced by a space.
    """
    return text.replace(" ", " ")


def find(name: str, page: int, start: str) -> Segment:
    """Find the first segment on a page whose text starts with `start`.

    Args:
        name: Sample file name.
        page: 1-based page number.
        start: Expected beginning of the text (thin spaces count as spaces).

    Returns:
        The matching segment.
    """
    for segment in segments(name):
        if segment.page == page and plain(segment.text).startswith(start):
            return segment
    raise AssertionError(f"no segment on page {page} starts with {start!r}")


# --- HPL care instructions: two columns, bold intro, bullets in an unmapped font ----------


def test_hpl_bold_intro_is_its_own_paragraph() -> None:
    assert find(HPL, 2, "herzlichen Glückwunsch").text.endswith("entschieden haben.")
    assert find(HPL, 2, "Matte Oberflächen").text.endswith("entwickelt:")


def test_hpl_bullets_become_list_items_without_the_bullet_glyph() -> None:
    items = [s for s in segments(HPL) if s.kind == "list_item"]

    assert len(items) == 41
    assert all("�" not in s.text and not s.warnings for s in items)
    assert find(HPL, 2, "Supermatte Struktur").kind == "list_item"


def test_hpl_columns_are_read_left_then_right() -> None:
    starts = [
        "Basic cleaning",
        "Cleaning agents",
        "So-called",
        "Intensive cleaning",
        "Cleaning must",
        "Special cleaning",
    ]
    orders = [find(HPL, 5, start).order for start in starts]

    assert orders == sorted(orders)


def test_hpl_headings_by_font_size() -> None:
    assert find(HPL, 2, "DE – Pflegehinweise HPL").kind == "heading"
    for heading in ["Basic cleaning", "Intensive cleaning", "Special cleaning"]:
        segment = find(HPL, 5, heading)
        assert (segment.text, segment.kind) == (heading, "heading")


def test_hpl_bold_closing_sentence_is_not_a_heading() -> None:
    assert find(HPL, 5, "We hope you enjoy").kind == "paragraph"


def test_hpl_cover_title_is_not_merged_with_small_labels() -> None:
    texts = [s.text for s in segments(HPL) if s.page == 1]

    assert not any("Onderhoudsaanwijzingen XTreme" in text for text in texts)


# --- Planning checklist: drawn checkboxes, question/answer form ---------------------------


def test_checklist_options_next_to_checkboxes_are_separate_list_items() -> None:
    options = [s.text for s in segments(CHECKLIST.format("DE")) if s.page == 5]
    items = [
        s.text for s in segments(CHECKLIST.format("DE")) if s.page == 5 and s.kind == "list_item"
    ]

    assert "Welchen Küchenstil bevorzugen Sie?" in options
    assert items[:9] == [
        "Grifflose Küchen",
        "Küchen mit Insel",
        "Moderne Küchen",
        "Dunkle Küchen",
        "Helle Küchen",
        "Küchenzeilen",
        "Farbenfrohe Küchen",
        "Küchen mit (Echt-)Holz",
        "Landhaus Küchen",
    ]


def test_checklist_footer_is_its_own_segment() -> None:
    assert any(s.text == "Checkliste | Seite 5" for s in segments(CHECKLIST.format("DE")))


@pytest.mark.parametrize("language", ["EN", "NL"])
def test_checklist_translations_have_the_same_structure(language: str) -> None:
    # The checklists share one layout, so they must produce the same number of list items.
    def count(name: str) -> int:
        return sum(s.kind == "list_item" for s in segments(name))

    assert count(CHECKLIST.format(language)) == count(CHECKLIST.format("DE"))


# --- Drawer flyer: two-page spread, ® fragments, captions in three languages --------------


def test_drawer_registered_mark_is_merged_into_its_line() -> None:
    assert any("Drawer Solutions® bilden eine optische Einheit" in s.text for s in segments(DRAWER))


def test_drawer_languages_are_separate_segments() -> None:
    assert find(DRAWER, 2, "EN – The Drawer Solutions")
    assert find(DRAWER, 2, "FR – Les Drawer Solutions")
    assert not any("DE – " in plain(s.text) and "EN – " in plain(s.text) for s in segments(DRAWER))


def test_drawer_large_title_words_are_not_list_items() -> None:
    assert not any(s.kind == "list_item" and s.font_size > 20 for s in segments(DRAWER))


# --- Catalogue ----------------------------------------------------------------------------


def test_catalog_page_numbers_are_not_headings() -> None:
    numbers = [s for s in segments(CATALOG) if s.text.strip().isdigit()]

    assert numbers
    assert all(s.kind == "paragraph" for s in numbers)


# --- every sample -------------------------------------------------------------------------


@pytest.mark.parametrize("path", sorted(SAMPLES.glob("*.pdf")), ids=lambda p: p.name[:30])
def test_every_sample_parses_into_clean_segments(path: Path) -> None:
    document = parse_pdf(path.read_bytes())

    assert document.segments
    assert [s.order for s in document.segments] == list(range(len(document.segments)))
    assert all(s.text == s.text.strip() and s.text for s in document.segments)
    assert all(not s.warnings for s in document.segments)
