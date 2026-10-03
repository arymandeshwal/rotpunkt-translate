import pytest

from app.parsers.pdf.text import UNREADABLE_WARNING, normalize_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Küche", "Küche"),  # combining diaeresis -> one character
        ("Hoch­schrank", "Hochschrank"),  # soft hyphen
        ("manu­", "manu"),  # soft hyphen at a line end
        ("Zerox​HPL", "ZeroxHPL"),  # zero-width space
        ("﻿Korpus", "Korpus"),  # byte order mark
        ("DE \x07Die Drawer", "DE Die Drawer"),  # control character
        ("\tGrifflose Küchen", " Grifflose Küchen"),  # tab -> space
        ("Zeile\neins", "Zeile eins"),
    ],
)
def test_normalizes_invisible_differences(raw: str, expected: str) -> None:
    assert normalize_text(raw) == (expected, set())


@pytest.mark.parametrize(
    "visible",
    [
        "Möbel-",  # line-end hyphen stays: hyphenation is left to the translator
        "Kühl-Gefrierkombination",
        "XT / FX",  # thin spaces are visible spacing
        "Zerox HPL XT Umbra",  # em space
        "40 cm",  # no-break space
        "Drawer Solutions®",
        "  leading and trailing  ",
        "",  # private-use glyph, e.g. an icon font
    ],
)
def test_leaves_visible_text_untouched(visible: str) -> None:
    assert normalize_text(visible) == (visible, set())


def test_unreadable_characters_are_kept_and_flagged() -> None:
    text, warnings = normalize_text("Schubk�sten")

    assert text == "Schubk�sten"
    assert warnings == {UNREADABLE_WARNING}
