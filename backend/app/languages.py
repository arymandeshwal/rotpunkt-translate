"""Languages the tool supports.

The list is mirrored by a CHECK constraint on glossary_terms.language, so adding a language
requires a migration as well.
"""

LANGUAGES: dict[str, str] = {
    "de": "German",
    "en": "English",
    "fr": "French",
    "nl": "Dutch",
    "da": "Danish",
    "nb": "Norwegian (Bokmål)",
    "es": "Spanish",
}

DEFAULT_SOURCE_LANGUAGE = "de"
