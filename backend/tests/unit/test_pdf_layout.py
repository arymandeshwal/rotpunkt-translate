from collections.abc import Sequence

from app.parsers.pdf import Segment, parse_pdf
from app.parsers.pdf.text import UNREADABLE_WARNING
from tests.pdf_factory import Box, Text, make_pdf, paragraph, text_width


def segments(*pages: Sequence[Text | Box], **page_size: float) -> list[Segment]:
    return parse_pdf(make_pdf(*pages, **page_size)).segments


def texts(*pages: Sequence[Text | Box], **page_size: float) -> list[str]:
    return [s.text for s in segments(*pages, **page_size)]


# --- paragraphs ----------------------------------------------------------------------------


def test_wrapped_lines_form_one_paragraph() -> None:
    lines = [
        "Matte Oberflächen liegen bereits seit einiger Zeit im Trend und",
        "finden häufig in den Korpus- und Frontteilen von Möbeln Verwendung.",
    ]

    assert texts(paragraph(lines)) == [" ".join(lines)]


def test_line_end_hyphen_is_kept_when_joining() -> None:
    assert texts(paragraph(["im Küchen- oder Möbel-", "handel"])) == [
        "im Küchen- oder Möbel- handel"
    ]


def test_vertical_gap_starts_a_new_paragraph() -> None:
    items = [*paragraph(["Erster Absatz."], y=100), *paragraph(["Zweiter Absatz."], y=140)]

    assert texts(items) == ["Erster Absatz.", "Zweiter Absatz."]


def test_switch_from_bold_to_regular_starts_a_new_paragraph() -> None:
    # HPL care instructions: a bold intro directly followed by regular text, same size.
    items = [
        Text("herzlichen Glückwunsch zum Erwerb Ihrer neuen Küche.", y=100, bold=True),
        Text("Matte Oberflächen liegen bereits seit einiger Zeit im Trend.", y=114),
    ]

    result = segments(items)
    assert [s.text for s in result] == [
        "herzlichen Glückwunsch zum Erwerb Ihrer neuen Küche.",
        "Matte Oberflächen liegen bereits seit einiger Zeit im Trend.",
    ]
    assert [s.bold for s in result] == [True, False]


def test_font_size_change_starts_a_new_paragraph() -> None:
    items = [Text("Pflegehinweise", y=100, size=20), Text("Basisreinigung mit Wasser.", y=122)]

    assert texts(items) == ["Pflegehinweise", "Basisreinigung mit Wasser."]


# --- classification ------------------------------------------------------------------------


def test_large_text_is_a_heading() -> None:
    body = paragraph(["Reinigen Sie die Oberfläche mit warmem Wasser.", "Danach trocknen."], y=130)
    result = segments([Text("Pflegehinweise", y=100, size=20), *body])

    assert [(s.kind, s.text) for s in result] == [
        ("heading", "Pflegehinweise"),
        ("paragraph", "Reinigen Sie die Oberfläche mit warmem Wasser. Danach trocknen."),
    ]


def test_short_bold_line_at_body_size_is_a_heading() -> None:
    items = [
        Text("Basic cleaning", y=100, bold=True),
        *paragraph(["Basic cleaning of XT / FX is usually done with hot water."], y=125),
    ]

    assert [s.kind for s in segments(items)] == ["heading", "paragraph"]


def test_bold_sentence_is_not_a_heading() -> None:
    items = [Text("Wir übernehmen keine Haftung für Schäden.", y=100, bold=True)]

    assert [s.kind for s in segments(items)] == ["paragraph"]


def test_segment_metadata() -> None:
    [segment] = segments([], [Text("Hochschrank", x=100, y=200, size=14, bold=True)])

    assert (segment.order, segment.page, segment.font_size, segment.bold) == (0, 2, 14, True)
    x0, y0, x1, y1 = segment.bbox
    assert x0 == 100 and y0 < 200 < y1 and x1 > x0


# --- lists ---------------------------------------------------------------------------------


def test_bullet_glyphs_start_list_items_and_are_removed() -> None:
    items = [
        Text("• Supermatte Struktur für Front und Arbeitsplatte mit allen", y=100),
        Text("  Qualitätsmerkmalen für Hochdruckschichtstoff.", x=80, y=114),
        Text("• Angenehm warme, samtig weiche Haptik.", y=128),
    ]

    result = segments(items)
    assert [(s.kind, s.text) for s in result] == [
        (
            "list_item",
            "Supermatte Struktur für Front und Arbeitsplatte mit allen "
            "Qualitätsmerkmalen für Hochdruckschichtstoff.",
        ),
        ("list_item", "Angenehm warme, samtig weiche Haptik."),
    ]


def test_unmapped_bullet_glyph_is_removed_and_not_flagged() -> None:
    # The test font has no glyph for BEL, so it becomes U+FFFD like the bullets in HPL_XTreme.
    [segment] = segments([Text("\x07Supermatte Struktur", y=100)])

    assert (segment.kind, segment.text) == ("list_item", "Supermatte Struktur")
    assert segment.warnings == set()


def test_unmapped_glyph_inside_a_word_stays_flagged() -> None:
    [segment] = segments([Text("\x07bersicht der Fronten", y=100)])

    assert segment.kind == "paragraph"
    assert segment.text.startswith("�")
    assert segment.warnings == {UNREADABLE_WARNING}


def test_lines_next_to_checkboxes_are_separate_list_items() -> None:
    # Planning checklist: tightly spaced options, each with a drawn checkbox to its left.
    options = ["Grifflose Küchen", "Küchen mit Insel", "Moderne Küchen"]
    items: list[Text | Box] = []
    for i, option in enumerate(options):
        baseline = 280 + i * 16
        items += [Box(179, baseline - 10, 206, baseline + 3), Text(option, x=215, y=baseline)]

    result = segments(items)
    assert [(s.kind, s.text) for s in result] == [("list_item", o) for o in options]


def test_drawings_far_from_text_do_not_make_list_items() -> None:
    items: list[Text | Box] = [
        Box(20, 90, 40, 105),
        *paragraph(["Erste Zeile ohne Kästchen,", "zweite Zeile."], x=200, y=100),
    ]

    assert [s.kind for s in segments(items)] == ["paragraph"]


# --- fragments -----------------------------------------------------------------------------


def test_pieces_of_one_visual_line_are_merged() -> None:
    # Drawer flyer: "® bilden" is stored separately from "Die Drawer Solutions",
    # and the space before "bilden" is part of that fragment.
    first = "Die Drawer Solutions"
    end = 72 + text_width(first)
    items = [
        Text(first, y=100),
        Text("® bilden eine optische Einheit.", x=end + 0.3, y=100),
    ]

    [segment] = segments(items)
    assert segment.text == "Die Drawer Solutions® bilden eine optische Einheit."
    assert segment.font_size == 11


def test_superscript_fragment_is_merged_into_its_line() -> None:
    first = "Drawer Solutions"
    end = 72 + text_width(first)
    items = [Text(first, y=100), Text("®", x=end + 0.3, y=96, size=6)]

    assert texts(items) == ["Drawer Solutions®"]


def test_text_on_the_same_row_in_different_columns_is_not_merged() -> None:
    items = [Text("Basic cleaning", x=21, y=100), Text("Intensive cleaning", x=319, y=100)]

    assert texts(items) == ["Basic cleaning", "Intensive cleaning"]


# --- reading order -------------------------------------------------------------------------


def two_column_page() -> list[Text | Box]:
    # Paragraph breaks line up across the columns, which defeats naive top-to-bottom sorting.
    left = [*paragraph(["L1 erste Zeile", "L1 zweite Zeile"], x=21, y=100)]
    left += paragraph(["L2 erste Zeile", "L2 zweite Zeile"], x=21, y=160)
    right = [*paragraph(["R1 erste Zeile", "R1 zweite Zeile"], x=319, y=100)]
    right += paragraph(["R2 erste Zeile", "R2 zweite Zeile"], x=319, y=160)
    return [*right, *left]  # stored in the "wrong" order on purpose


def test_columns_are_read_one_after_the_other() -> None:
    assert [t.split()[0] for t in texts(two_column_page())] == ["L1", "L2", "R1", "R2"]


def test_full_width_title_and_footer_frame_the_columns() -> None:
    items = [
        Text("Seite 5", x=280, y=820, size=8),
        *two_column_page(),
        Text("DE – Pflegehinweise HPL (XT + FX)", x=21, y=50, size=16),
    ]

    order = [t.split()[0] for t in texts(items)]
    assert order == ["DE", "L1", "L2", "R1", "R2", "Seite"]


def test_spread_pages_read_left_page_then_right_page() -> None:
    items = [
        *paragraph(["Rechte Seite Text"], x=900, y=100),
        *paragraph(["Linke Seite Text"], x=40, y=300),
    ]

    assert texts(items, width=1190, height=420) == ["Linke Seite Text", "Rechte Seite Text"]


def test_order_continues_across_pages() -> None:
    result = segments(
        [Text("Seite eins", y=100)], [], [Text("Seite drei A", y=100), Text("Seite drei B", y=200)]
    )

    assert [(s.order, s.page, s.text) for s in result] == [
        (0, 1, "Seite eins"),
        (1, 3, "Seite drei A"),
        (2, 3, "Seite drei B"),
    ]


def test_headers_footers_and_page_numbers_become_segments() -> None:
    items = [
        Text("Rotpunkt Küchen – Pflegehinweise", y=30, size=8),
        *paragraph(["Basisreinigung mit warmem Wasser."], y=400),
        Text("3", x=290, y=820, size=8),
    ]

    assert texts(items) == [
        "Rotpunkt Küchen – Pflegehinweise",
        "Basisreinigung mit warmem Wasser.",
        "3",
    ]


def test_page_info_is_returned_for_every_page() -> None:
    document = parse_pdf(make_pdf([Text("A")], [], width=298, height=420))

    assert [(p.number, p.width, p.height) for p in document.pages] == [(1, 298, 420), (2, 298, 420)]
