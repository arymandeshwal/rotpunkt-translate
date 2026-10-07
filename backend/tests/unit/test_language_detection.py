from app.services.language_detection import is_translatable


def test_is_translatable_pure_source_language() -> None:
    # High confidence German
    assert is_translatable("Bitte beachten Sie die neuen Montagehinweise.", "de") is True
    assert is_translatable("Hochschränke und Unterschränke", "de") is True


def test_is_translatable_high_confidence_foreign() -> None:
    # High confidence English/French, should be skipped (False) when source is German
    assert is_translatable("Please note the new assembly instructions.", "de") is False
    assert is_translatable("Armoires hautes et meubles bas", "de") is False

    # If the source is actually English, the English text should be translated
    assert is_translatable("Please note the new assembly instructions.", "en") is True


def test_is_translatable_mixed_and_low_confidence() -> None:
    # Mixed German and English (Top language might be English, but confidence < 0.70)
    assert is_translatable("Grifflos / Handleless design", "de") is True

    # Mixed German and English (Top language is German)
    assert is_translatable("Korpusstärke (Carcase thickness): 19mm", "de") is True

    # Short foreign phrase, confidence < 0.70, should be safely sent to translation
    assert is_translatable("Tall units and base units", "de") is True

    # Single obscure words sometimes get misclassified by Lingua
    assert is_translatable("Korpusdekore", "de") is True


def test_is_translatable_numbers_and_codes() -> None:
    # Numbers, dimensions, and item codes should never be dropped
    assert is_translatable("19 mm", "de") is True
    assert is_translatable("120 x 60 cm", "de") is True
    assert is_translatable("G500-12X", "de") is True
    assert is_translatable("2026", "de") is True
    assert is_translatable("X", "de") is True
    assert is_translatable("", "de") is True
    assert is_translatable("   ", "de") is True
