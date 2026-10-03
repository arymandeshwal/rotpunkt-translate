import re

import pytest

from app.parsers.pdf import TextLine, extract
from app.parsers.pdf.text import UNREADABLE_WARNING
from tests.pdf_factory import Text, make_pdf


def line_texts(pdf: bytes) -> list[str]:
    return [line.text for page in extract(pdf).pages for line in page.lines]


def only_line(pdf: bytes) -> TextLine:
    lines = [line for page in extract(pdf).pages for line in page.lines]
    assert len(lines) == 1
    return lines[0]


def test_extracts_text_with_umlauts() -> None:
    pdf = make_pdf([Text("Spülunterschrank für die Küche")])

    assert line_texts(pdf) == ["Spülunterschrank für die Küche"]


def test_page_metadata() -> None:
    pdf = make_pdf([Text("A")], [Text("B")], width=298, height=420)

    pages = extract(pdf).pages
    assert [(p.number, p.width, p.height) for p in pages] == [(1, 298, 420), (2, 298, 420)]
    assert [p.lines[0].text for p in pages] == ["A", "B"]


def test_line_position() -> None:
    line = only_line(make_pdf([Text("Hochschrank", x=100, y=200, size=12)]))

    x0, y0, x1, y1 = line.bbox
    assert x0 == pytest.approx(100, abs=1)
    assert y0 < 200 < y1  # the baseline lies inside the box
    assert x1 > x0


def test_font_size_and_bold() -> None:
    pdf = make_pdf([Text("Pflegehinweise", size=20, bold=True), Text("Basisreinigung", y=120)])

    heading, body = extract(pdf).pages[0].lines
    assert (heading.font_size, heading.bold) == (20, True)
    assert (body.font_size, body.bold) == (11, False)


def test_header_footer_and_page_number_are_extracted() -> None:
    pdf = make_pdf(
        [
            Text("Rotpunkt Küchen – Pflegehinweise", y=30, size=8),
            Text("Basisreinigung mit warmem Wasser", y=400),
            Text("Seite 3", x=500, y=820, size=8),
        ]
    )

    assert line_texts(pdf) == [
        "Rotpunkt Küchen – Pflegehinweise",
        "Basisreinigung mit warmem Wasser",
        "Seite 3",
    ]


def test_normalizes_but_keeps_the_raw_text() -> None:
    line = only_line(make_pdf([Text("Hoch­schrank Küche XT / FX")]))

    assert line.text == "Hochschrank Küche XT / FX"
    assert line.raw_text == "Hoch­schrank Küche XT / FX"


def test_line_end_hyphen_is_kept() -> None:
    pdf = make_pdf([Text("im Küchen- oder Möbel-", y=100), Text("handel", y=115)])

    assert line_texts(pdf) == ["im Küchen- oder Möbel-", "handel"]


def test_unreadable_glyphs_are_flagged() -> None:
    # The test font has no glyph for BEL, so the PDF stores an unmapped character.
    line = only_line(make_pdf([Text("Schubk\x07sten")]))

    assert "�" in line.text
    assert line.warnings == {UNREADABLE_WARNING}


def test_blank_page_has_no_lines() -> None:
    pdf = make_pdf([Text("Seite eins")], [])

    pages = extract(pdf).pages
    assert len(pages) == 2
    assert pages[1].lines == []


def test_no_text_is_lost() -> None:
    words = [
        "Korpus",
        "Front",
        "Arbeitsplatte",
        "Schubkasten",
        "Auszug",
        "grifflos",
        "Hochschrank",
        "Unterschrank",
        "Spülunterschrank",
        "Eckschrank",
        "Kochfeld",
        "Dunstabzugshaube",
        "Geschirrspülmaschine",
        "Zerox",
        "HPL",
        "XT",
        "FENIX",
        "Drawer",
        "Solutions®",
        "21103380",
    ]
    items = [Text(" ".join(words[i : i + 4]), y=60 + 20 * i) for i in range(0, len(words), 4)]

    extracted = extract(make_pdf(items, [Text("Seite 2", y=800)]))

    assert re.findall(r"\S+", extracted.text) == [*words, "Seite", "2"]
