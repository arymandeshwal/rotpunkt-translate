import asyncio
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv()

DATA_PATH = Path(__file__).parent / "data" / "rotpunkt_eval_annotations.json"


async def run_gemini_eval():
    dataset = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    eval_subset = [d for d in dataset if d["category"] in ["F3", "F4", "Clean"]]

    # Try gemini-3.8-flash since 3.5 works on this key
    client = genai.Client(vertexai=True, api_key=os.environ["GEMINI_API_KEY"])
    model_name = "gemini-3.8-flash"

    prompt = """
You are a translation QA assistant for a kitchen manufacturer.
Extract words from the segments into these categories:
- "kitchen_trade_term": Technical manufacturing material or jargon.
- "ambiguous_term": Words with multiple valid translations in a kitchen context.

IMPORTANT: Do not use these exact examples if they aren't in the text, but use them to understand the concept:
Examples of trade terms: "polyurethane", "dowel", "chipboard", "HDF", "hinge".
Examples of ambiguous terms: "reveal", "profile", "return", "plinth", "clearance".
Examples of normal words (DO NOT extract): "warranty", "receipt", "dry", "attach", "clean", "department".

Return a JSON array of arrays. Each inner array must have objects with "text" and "type". If nothing matches, return [].

INPUT SEGMENTS:
"""
    texts = [item["text"] for item in eval_subset]

    batch_size = 20
    results = []

    print(f"Running F3/F4 Annotation Eval using {model_name}...")

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt + json.dumps(batch, ensure_ascii=False),
                config=types.GenerateContentConfig(
                    temperature=0.0, response_mime_type="application/json"
                ),
            )

            raw_json = response.text
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:-3]

            batch_results = json.loads(raw_json)

            if len(batch_results) == len(batch):
                results.extend(batch_results)
            else:
                print(
                    f"Warning: Batch size mismatch. Expected {len(batch)}, got {len(batch_results)}."
                )
                results.extend([[] for _ in batch])

        except Exception as e:
            print(f"Error on batch: {e}")
            results.extend([[] for _ in batch])

    stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    for item, llm_ann in zip(eval_subset, results):
        cat = item["category"]
        exp_set = {
            (e["type"], e["text"].lower())
            for e in item["expected_annotations"]
            if e["type"] in ["kitchen_trade_term", "ambiguous_term"]
        }
        act_set = {
            (a["type"], a["text"].lower())
            for a in llm_ann
            if a["type"] in ["kitchen_trade_term", "ambiguous_term"]
        }

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
    print(f" ROTPUNKT F3/F4 ({model_name.upper()}) EVALUATION REPORT ".center(80))
    print("=" * 80 + "\n")
    print(tabulate(summary, headers="keys", tablefmt="github"))
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(run_gemini_eval())
