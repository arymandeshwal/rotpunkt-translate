from app.services.highlighting import compute_deterministic_annotations
from app.services.translation_service import GlossaryTermInfo


def test_highlighting_glossary():
    translated_text = "The Cabinet body is available in various colors."
    glossary = [
        GlossaryTermInfo(
            entry_id=1,
            source_text="Korpus",
            target_text="Cabinet body",
            is_dnt=False,
            is_case_sensitive=False,
        )
    ]

    annotations = compute_deterministic_annotations(translated_text, glossary)
    assert len(annotations) == 1
    assert annotations[0]["start"] == 4
    assert annotations[0]["end"] == 16
    assert annotations[0]["type"] == "glossary"
    assert annotations[0]["term_id"] == 1
    assert annotations[0]["text"] == "Cabinet body"


def test_highlighting_dnt():
    translated_text = "The new Greenline series is amazing."
    glossary = [
        GlossaryTermInfo(
            entry_id=2,
            source_text="Greenline",
            target_text="Greenline",
            is_dnt=True,
            is_case_sensitive=True,
        )
    ]

    annotations = compute_deterministic_annotations(translated_text, glossary)
    assert len(annotations) == 1
    assert annotations[0]["type"] == "dnt"
    assert annotations[0]["term_id"] == 2
    assert annotations[0]["text"] == "Greenline"
    assert annotations[0]["start"] == 8


def test_highlighting_case_insensitivity():
    # Model capitalized 'Body'
    translated_text = "The Cabinet Body is white."
    glossary = [
        GlossaryTermInfo(
            entry_id=1,
            source_text="Korpus",
            target_text="Cabinet body",
            is_dnt=False,
            is_case_sensitive=False,
        )
    ]

    annotations = compute_deterministic_annotations(translated_text, glossary)
    assert len(annotations) == 1
    assert annotations[0]["text"] == "Cabinet Body"


def test_highlighting_overlaps():
    # Longest match should win
    translated_text = "I love Rotpunkt Küchen."
    glossary = [
        GlossaryTermInfo(
            entry_id=1,
            source_text="Rotpunkt",
            target_text="Rotpunkt",
            is_dnt=True,
            is_case_sensitive=False,
        ),
        GlossaryTermInfo(
            entry_id=2,
            source_text="Rotpunkt Küchen",
            target_text="Rotpunkt Küchen",
            is_dnt=True,
            is_case_sensitive=False,
        ),
    ]

    annotations = compute_deterministic_annotations(translated_text, glossary)
    assert len(annotations) == 1
    assert annotations[0]["text"] == "Rotpunkt Küchen"
    assert annotations[0]["term_id"] == 2


def test_highlighting_boundary():
    # Should not match substrings inside words
    translated_text = "The greenlineX series."
    glossary = [
        GlossaryTermInfo(
            entry_id=1,
            source_text="Greenline",
            target_text="greenline",
            is_dnt=True,
            is_case_sensitive=False,
        )
    ]

    annotations = compute_deterministic_annotations(translated_text, glossary)
    assert len(annotations) == 0


def test_multiple_occurrences():
    translated_text = "The front is clean. Please dry the front."
    glossary = [
        GlossaryTermInfo(
            entry_id=1,
            source_text="Front",
            target_text="front",
            is_dnt=False,
            is_case_sensitive=False,
        )
    ]

    annotations = compute_deterministic_annotations(translated_text, glossary)
    assert len(annotations) == 2
    assert annotations[0]["text"] == "front"
    assert annotations[1]["text"] == "front"
    assert annotations[0]["start"] < annotations[1]["start"]
