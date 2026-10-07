import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

load_dotenv()

from typesafe_sdk import Choice, TypeSafeClient


def extract_ngrams(text, max_n=3):
    words = text.split()
    ngrams = set()
    for n in range(1, max_n + 1):
        for i in range(len(words) - n + 1):
            chunk = " ".join(words[i : i + n])
            chunk = chunk.strip(".,;:!?()[]{}")
            if chunk and len(chunk) > 2:
                ngrams.add(chunk)
    return list(ngrams)


def test_jev_highlighting():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("No OPENROUTER_API_KEY found.")
        return

    client = TypeSafeClient(
        api_key=api_key,
        base_url="https://openrouter.ai/api",
        model="~typesafe/jev-latest",
    )

    test_sentences = [
        "Attach the filler panel to the fascia.",  # Ambiguous F4
        "The melamine resin coated panels are standard.",  # Trade term F3
        "The C4binet b0dy is made of solid w00d.",  # Faulty F5
        "In the event of a warranty claim, please contact the customer service department with your original receipt.",  # Clean
    ]

    for text in test_sentences:
        chunks = extract_ngrams(text, max_n=3)
        questions = {}
        for i, chunk in enumerate(chunks):
            questions[f"chunk_{i}"] = Choice(
                instructions=f"Analyze the specific phrase '{chunk}' within the context of the sentence. Which category does it belong to?",
                criteria={
                    "trade_term": "A highly technical kitchen manufacturing material, part, or industry jargon (e.g. melamine, resin coated, edge banding).",
                    "ambiguous_term": "A word with multiple translation meanings in a kitchen context requiring human review (e.g. filler panel, fascia, reveal, profile).",
                    "faulty_term": "A misspelled word, OCR artifact, or corrupted text (e.g. w00d, C4binet).",
                    "none": "A normal word, standard instructional text, common noun, verb, or adjective (e.g. warranty, receipt, clean, attach, dry).",
                },
            )

        print(f"\n--- Testing: '{text}' ---")
        start = time.perf_counter()
        response = client.system_one(state=text, questions=questions)
        elapsed = time.perf_counter() - start

        print(f"Latency: {elapsed * 1000:.0f}ms for {len(chunks)} parallel questions")

        for i, chunk in enumerate(chunks):
            ans = response.answers[f"chunk_{i}"]
            # Only print if JEV thinks it's a highlight or if it's very unsure
            if ans.choice != "none":
                print(f"[HIGHLIGHT] '{chunk}' -> {ans.choice.upper()} (conf: {ans.confidence:.2f})")
            elif ans.confidence < 0.6:
                print(f"[UNSURE]    '{chunk}' -> {ans.choice} (conf: {ans.confidence:.2f})")


if __name__ == "__main__":
    test_jev_highlighting()
