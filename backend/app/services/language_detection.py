from lingua import Language, LanguageDetectorBuilder

from app.languages import LanguageCode

# Map our ISO codes to Lingua Language enums
_LINGUA_MAP: dict[LanguageCode, Language] = {
    "de": Language.GERMAN,
    "en": Language.ENGLISH,
    "fr": Language.FRENCH,
    "nl": Language.DUTCH,
    "da": Language.DANISH,
    "nb": Language.BOKMAL,
    "es": Language.SPANISH,
}

# Build a detector supporting exactly the languages our application supports.
_detector = LanguageDetectorBuilder.from_languages(*_LINGUA_MAP.values()).build()

# The confidence threshold above which we trust the detector that a segment
# is purely in a foreign language and should not be translated.
_FOREIGN_LANGUAGE_THRESHOLD = 0.75


def detect_primary_language(text: str) -> LanguageCode | None:
    """Detect the most likely language of a text segment.

    Returns None if the text is too short/ambiguous (e.g. numbers, item codes)
    or if no language can be reliably detected.
    """
    if not text or not text.strip():
        return None

    result = _detector.detect_language_of(text)
    if result is None:
        return None

    for iso, lingua_enum in _LINGUA_MAP.items():
        if lingua_enum == result:
            return iso
    return None


def is_translatable(text: str, source_language: LanguageCode) -> bool:
    """Determine if a text segment should be translated.

    Uses language detection to filter out segments that are confidently in a language
    other than the project's source language.

    Args:
        text: The text segment to evaluate.
        source_language: The ISO code of the document's source language (e.g., "de").

    Returns:
        False if the text is confidently detected as a DIFFERENT language.
        True in all other cases (matches source language, mixed languages, numbers,
        codes, or low-confidence foreign text).
    """
    if not text or not text.strip():
        # Default to True for empty/whitespace to avoid dropping layout segments
        return True

    lingua_source = _LINGUA_MAP.get(source_language)
    if not lingua_source:
        # Unknown source language, play it safe
        return True

    # Get confidence values for all detected languages in the text
    confidence_values = _detector.compute_language_confidence_values(text)

    if not confidence_values:
        # Cannot detect any language (e.g., just numbers like "19mm")
        return True

    top_match = confidence_values[0]

    # If the top match is NOT our source language, and the detector is highly
    # confident about it, we assume it's a pure block of foreign text and skip it.
    if top_match.language != lingua_source and top_match.value >= _FOREIGN_LANGUAGE_THRESHOLD:
        return False

    # In all other cases (matches source, mixed text, or low confidence), translate it.
    return True
