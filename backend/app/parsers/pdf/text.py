"""Minimal, lossless text normalization for extracted PDF text.

Only changes that alter no visible character are applied, so glossary matching works on the
same characters the reader sees. Hyphenation and line breaks are left for the translation
engine to handle.
"""

import unicodedata

REPLACEMENT_CHARACTER = "�"
UNREADABLE_WARNING = "unreadable_characters"


def normalize_text(raw: str) -> tuple[str, set[str]]:
    """Normalize extracted text without changing any visible character.

    - Unicode NFC, so "u" + combining diaeresis becomes the single character "ü".
    - Invisible format characters (soft hyphen, zero-width space, BOM, ...) are removed.
    - Control characters are removed; tab, newline and carriage return become a space.

    Args:
        raw: Text exactly as extracted from the PDF.

    Returns:
        (normalized text, warnings). The warnings contain UNREADABLE_WARNING if the text has
        characters the PDF font could not map to Unicode (U+FFFD); those are kept.
    """
    text = unicodedata.normalize("NFC", raw)
    kept: list[str] = []
    for char in text:
        category = unicodedata.category(char)
        if category == "Cf":
            continue
        if category == "Cc":
            if char in "\t\n\r":
                kept.append(" ")
            continue
        kept.append(char)
    normalized = "".join(kept)

    warnings: set[str] = set()
    if REPLACEMENT_CHARACTER in normalized:
        # The PDF font has no Unicode mapping for some glyphs; the text cannot be recovered.
        warnings.add(UNREADABLE_WARNING)
    return normalized, warnings
