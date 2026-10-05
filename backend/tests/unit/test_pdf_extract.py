import re

import pytest

from app.parsers.pdf import TextLine
from app.parsers.pdf.extract import extract
from app.parsers.pdf.text import UNREADABLE_WARNING
from tests.pdf_factory import Box, Text, make_pdf, text_width


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


def test_mixed_size_line_is_split() -> None:
    # HPL cover: PyMuPDF puts a 7 pt label and a 33 pt title word on one line, joined by a
    # 33 pt space span.
    label = "Onderhoudsaanwijzingen"
    end = 40 + text_width(label, size=7)
    pdf = make_pdf([Text(label, x=40, y=380, size=7), Text("XTreme", x=end + 20, y=385, size=33)])

    small, large = extract(pdf).pages[0].lines
    assert (small.text.strip(), small.font_size) == (label, 7)
    assert (large.text.strip(), large.font_size) == ("XTreme", 33)
    assert small.bbox[3] - small.bbox[1] < 12  # the 33 pt space does not inflate the box


def test_superscript_stays_on_its_line() -> None:
    first = "Drawer Solutions"
    end = 72 + text_width(first)

    pdf = make_pdf([Text(first, y=100), Text("®", x=end + 0.3, y=96, size=6)])

    assert [line.font_size for line in extract(pdf).pages[0].lines] == [11]


def test_small_drawn_shapes_are_returned_as_markers() -> None:
    # Planning checklist: checkboxes are drawn 27 x 13 pt rectangles.
    page = extract(make_pdf([Box(179, 271, 206, 284), Text("Grifflose Küchen", x=215, y=282)]))

    [marker] = page.pages[0].markers
    assert marker == pytest.approx((179, 271, 206, 284), abs=1)


@pytest.mark.parametrize(
    "box",
    [
        Box(20, 20, 575, 400),  # background panel
        Box(20, 100, 575, 101),  # thin rule line
        Box(20, 100, 21, 101),  # speck
    ],
    ids=["panel", "rule", "speck"],
)
def test_large_or_tiny_shapes_are_not_markers(box: Box) -> None:
    assert extract(make_pdf([box, Text("Text")])).pages[0].markers == []


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
