import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv()

from typesafe_sdk import Choice, TypeSafeClient

DATA_PATH = Path(__file__).parent / "data" / "rotpunkt_eval_annotations.json"


def extract_ngrams_with_positions(text, max_n=3):
    """Extract n-grams and their start/end positions in the text."""
    import re

    # Find all words and their spans
    words = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\b\w+\b", text)]

    ngrams = []
    for n in range(1, max_n + 1):
        for i in range(len(words) - n + 1):
            start = words[i][1]
            end = words[i + n - 1][2]
            chunk = text[start:end]
            # avoid purely numeric or tiny chunks if we want, but let's keep it simple
            if len(chunk) > 2:
                ngrams.append((chunk, start, end))
    return ngrams


def resolve_overlaps(annotations):
    """Keep the longest match, discard overlapping shorter ones."""
    annotations.sort(key=lambda x: x["end"] - x["start"], reverse=True)
    kept = []

    def is_overlapping(start, end):
        for k in kept:
            if start < k["end"] and end > k["start"]:
                return True
        return False

    for ann in annotations:
        if not is_overlapping(ann["start"], ann["end"]):
            kept.append(ann)
    return kept


def run_jev_eval():
    dataset = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    client = TypeSafeClient(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api",
        model="~typesafe/jev-latest",
    )

    stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    print("Running JEV Eval for F3, F4, and Clean...")

    # Filter dataset to just F3, F4, and Clean to save time/tokens for this specific metric check
    eval_subset = [d for d in dataset if d["category"] in ["F3", "F4", "Clean"]]

    for item in eval_subset:
        text = item["text"]
        cat = item["category"]
        expected = item["expected_annotations"]

        ngrams = extract_ngrams_with_positions(text, max_n=3)
        if not ngrams:
            continue

        questions = {}
        for i, (chunk, _, _) in enumerate(ngrams):
            questions[f"chunk_{i}"] = Choice(
                instructions=f"Analyze the exact phrase '{chunk}' within the sentence. Which category does it belong to?",
                criteria={
                    "kitchen_trade_term": "A specific kitchen component, hardware, appliance, or material (e.g. carcase, laminate, pull-out, worktop, MDF, hob, hinge, edge banding).",
                    "ambiguous_term": "Generic structural words (e.g. panel, board, unit, cover, gap, filler, fascia) whose precise translation depends on their physical location in the kitchen layout.",
                    "faulty_term": "A misspelled word, OCR artifact, or corrupted text.",
                    "none": "Any standard word, verb, adjective, or general text that is not a specialized kitchen term.",
                },
            )

        try:
            response = client.system_one(state=text, questions=questions)
        except Exception as e:
            print(f"Error on '{text}': {e}")
            continue

        raw_annotations = []
        for i, (chunk, start, end) in enumerate(ngrams):
            ans = response.answers.get(f"chunk_{i}")
            if ans and ans.choice != "none" and ans.confidence >= 0.6:
                raw_annotations.append(
                    {"start": start, "end": end, "type": ans.choice, "text": chunk}
                )

        final_annotations = resolve_overlaps(raw_annotations)

        # Scoring
        exp_set = {(e["type"], e["text"].lower()) for e in expected}
        act_set = {(a["type"], a["text"].lower()) for a in final_annotations}

        tp = len(exp_set.intersection(act_set))
        fp = len(act_set - exp_set)
        fn = len(exp_set - act_set)

        stats[cat]["tp"] += tp
        stats[cat]["fp"] += fp
        stats[cat]["fn"] += fn

    summary = []
    for cat, s in stats.items():
        tp, fp, fn = s["tp"], s["fp"], s["fn"]
        precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else (100.0 if fp == 0 else 0.0)
        recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else (100.0 if fn == 0 else 0.0)

        summary.append(
            {
                "Category": cat,
                "True Positives": tp,
                "False Positives": fp,
                "False Negatives": fn,
                "Precision": f"{precision:.1f}%",
                "Recall": f"{recall:.1f}%",
            }
        )

    print("\n" + "=" * 80)
    print(" ROTPUNKT F3/F4 (JEV) EVALUATION REPORT ".center(80))
    print("=" * 80 + "\n")
    print(tabulate(summary, headers="keys", tablefmt="github"))
    print("\n" + "=" * 80)


if __name__ == "__main__":
    run_jev_eval()
