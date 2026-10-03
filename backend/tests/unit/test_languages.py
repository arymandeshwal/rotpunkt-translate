from typing import get_args

from app.languages import DEFAULT_SOURCE_LANGUAGE, LANGUAGES, LanguageCode


def test_language_code_type_matches_language_table() -> None:
    assert get_args(LanguageCode) == tuple(LANGUAGES)


def test_default_source_language_is_supported() -> None:
    assert DEFAULT_SOURCE_LANGUAGE in LANGUAGES
