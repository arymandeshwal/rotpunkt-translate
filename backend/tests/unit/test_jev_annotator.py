from unittest.mock import MagicMock, patch

from app.services.jev_annotator import (
    extract_ngrams_with_positions,
    process_single_text,
    resolve_overlaps,
)


def test_extract_ngrams():
    text = "Attach the filler"
    ngrams, unigrams = extract_ngrams_with_positions(text, max_n=3)

    ngram_texts = [n[0] for n in ngrams]
    assert "Attach" in ngram_texts
    assert "the" in ngram_texts
    assert "filler" in ngram_texts
    assert "Attach the" in ngram_texts
    assert "the filler" in ngram_texts
    assert "Attach the filler" in ngram_texts


def test_resolve_overlaps():
    # Longest should win
    annotations = [
        {"start": 11, "end": 17, "type": "ambiguous_term", "text": "filler"},
        {"start": 11, "end": 23, "type": "ambiguous_term", "text": "filler panel"},
        {"start": 18, "end": 23, "type": "none", "text": "panel"},
    ]
    kept = resolve_overlaps(annotations)
    assert len(kept) == 1
    assert kept[0]["text"] == "filler panel"


@patch("app.services.jev_annotator.TypeSafeClient")
def test_process_single_text_mocked(mock_client_class):
    mock_client = MagicMock()

    # We will mock the responses for Stage 1 and Stage 2
    # Stage 1: "filler panel" and "filler" and "panel" are specialized. "Attach" and "the" are generic.

    def mock_system_one(state, questions):
        mock_response = MagicMock()
        mock_response.answers = {}

        # If it's stage 1 (keys have generic/specialized)
        is_stage1 = False
        if questions and "chunk_0" in questions:
            is_stage1 = "specialized" in questions["chunk_0"].criteria

        for k, q in questions.items():
            ans_mock = MagicMock()
            chunk_text = q.instructions.split("'")[1]

            if is_stage1:
                if "filler" in chunk_text or "panel" in chunk_text:
                    ans_mock.choice = "specialized"
                    ans_mock.probabilities = {"specialized": 0.9}
                else:
                    ans_mock.choice = "generic"
                    ans_mock.probabilities = {"generic": 0.9}
            else:
                # Stage 2
                ans_mock.choice = "ambiguous_term"
                ans_mock.probabilities = {"ambiguous_term": 0.8}

            mock_response.answers[k] = ans_mock

        return mock_response

    mock_client.system_one.side_effect = mock_system_one

    text = "Attach the filler panel"
    annotations = process_single_text(mock_client, text)

    assert len(annotations) == 1
    assert annotations[0]["text"] == "filler panel"
    assert annotations[0]["type"] == "ambiguous_term"
