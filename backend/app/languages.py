"""Languages the tool supports.

The list is mirrored by a CHECK constraint on glossary_terms.language, so adding a language
requires a migration as well. LanguageCode and LANGUAGES must list the same codes.
"""

from typing import Literal

LanguageCode = Literal["de", "en", "fr", "nl", "da", "nb", "es"]

LANGUAGES: dict[LanguageCode, str] = {
    "de": "German",
    "en": "English",
    "fr": "French",
    "nl": "Dutch",
    "da": "Danish",
    "nb": "Norwegian (Bokmål)",
    "es": "Spanish",
}

DEFAULT_SOURCE_LANGUAGE: LanguageCode = "de"
