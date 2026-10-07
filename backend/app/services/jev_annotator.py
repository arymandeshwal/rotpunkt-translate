import asyncio
import re
from typing import Any

from typesafe_sdk import Choice, TypeSafeClient

from app.config import get_settings

# Using 0.60 raw probability as proven in the eval
PROBABILITY_THRESHOLD = 0.60


def _get_client() -> TypeSafeClient | None:
    api_key = get_settings().openrouter_api_key
    if not api_key:
        return None
    return TypeSafeClient(
        api_key=api_key,
        base_url="https://openrouter.ai/api",
        model="~typesafe/jev-latest",
    )


def extract_ngrams_with_positions(text: str, max_n: int = 3) -> tuple[list, list]:
    words = [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\b\w+\b", text)]
    ngrams = []
    unigrams = []
    for n in range(1, max_n + 1):
        for i in range(len(words) - n + 1):
            start = words[i][1]
            end = words[i + n - 1][2]
            chunk = text[start:end]
            if len(chunk) > 2:
                ngrams.append((chunk, start, end))
            if n == 1:
                unigrams.append((chunk, start, end))
    return ngrams, unigrams


def resolve_overlaps(annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotations.sort(key=lambda x: x["end"] - x["start"], reverse=True)
    kept = []

    def is_overlapping(start: int, end: int) -> bool:
        for k in kept:
            if start < k["end"] and end > k["start"]:
                return True
        return False

    for ann in annotations:
        if not is_overlapping(ann["start"], ann["end"]):
            kept.append(ann)
    return kept


def process_single_text(client: TypeSafeClient, text: str) -> list[dict[str, Any]]:
    """Process a single segment text via JEV 2-stage hierarchical classification."""
    ngrams, unigrams = extract_ngrams_with_positions(text, max_n=3)
    if not ngrams:
        return []

    # STAGE 1: Is it specialized or generic?
    q1 = {}
    for i, (chunk, _, _) in enumerate(ngrams):
        q1[f"chunk_{i}"] = Choice(
            instructions=f"Does the phrase '{chunk}' have a specialized meaning in kitchen manufacturing, or is it a generic word?",
            criteria={
                "specialized": "A kitchen part, material, layout term, or corrupted text.",
                "generic": "A normal everyday word (e.g. warranty, receipt, attach, the, dry, please, read, to, use, before, if, with, a, in, of).",
            },
        )

    try:
        res1 = client.system_one(state=text, questions=q1)
    except Exception:
        return []

    unigram_is_specialized = {}
    stage2_ngrams = []

    for i, (chunk, start, end) in enumerate(ngrams):
        ans = res1.answers.get(f"chunk_{i}")
        prob = ans.probabilities.get(ans.choice, 0) if ans and ans.probabilities else 0
        is_spec = bool(ans and ans.choice == "specialized" and prob >= PROBABILITY_THRESHOLD)

        # Populate unigram lookup
        for _, u_start, u_end in unigrams:
            if start == u_start and end == u_end:
                unigram_is_specialized[(u_start, u_end)] = is_spec
                break

        if is_spec:
            stage2_ngrams.append((i, chunk, start, end))

    if not stage2_ngrams:
        return []

    # STAGE 2: What kind of specialized term?
    q2 = {}
    for idx, chunk, _, _ in stage2_ngrams:
        q2[f"chunk_{idx}"] = Choice(
            instructions=f"Analyze the specialized kitchen phrase '{chunk}'. Which category fits best?",
            criteria={
                "kitchen_trade_term": "A highly specific, unambiguous kitchen material or hardware (e.g. melamine, resin, MDF, edge banding).",
                "ambiguous_term": "A generic structural layout term whose exact translation depends on context (e.g. panel, filler, fascia, gap, corner).",
            },
        )

    try:
        res2 = client.system_one(state=text, questions=q2)
    except Exception:
        return []

    raw_annotations = []
    for idx, chunk, start, end in stage2_ngrams:
        ans = res2.answers.get(f"chunk_{idx}")
        prob = ans.probabilities.get(ans.choice, 0) if ans and ans.probabilities else 0

        if ans and prob >= PROBABILITY_THRESHOLD:
            # Boundary trimming logic
            chunk_unis = [u for u in unigrams if u[1] >= start and u[2] <= end]

            while chunk_unis and not unigram_is_specialized.get(
                (chunk_unis[0][1], chunk_unis[0][2]), False
            ):
                chunk_unis.pop(0)

            while chunk_unis and not unigram_is_specialized.get(
                (chunk_unis[-1][1], chunk_unis[-1][2]), False
            ):
                chunk_unis.pop()

            if chunk_unis:
                new_start = chunk_unis[0][1]
                new_end = chunk_unis[-1][2]
                new_chunk = text[new_start:new_end]
                raw_annotations.append(
                    {
                        "start": new_start,
                        "end": new_end,
                        "type": ans.choice,
                        "text": new_chunk,
                    }
                )

    final_annotations = resolve_overlaps(raw_annotations)
    # Sort for reading order
    final_annotations.sort(key=lambda x: x["start"])
    return final_annotations


async def compute_ai_annotations(translated_texts: list[str]) -> list[list[dict[str, Any]]]:
    """
    Use JEV to compute F3 (kitchen_trade_term) and F4 (ambiguous_term) annotations for a batch of translated texts.
    Returns a list of annotations for each input text.
    """
    client = _get_client()
    if not client:
        # Silently return empty annotations if OpenRouter key isn't provided
        return [[] for _ in translated_texts]

    loop = asyncio.get_running_loop()
    # Run all texts through JEV in parallel background threads
    tasks = [
        loop.run_in_executor(None, process_single_text, client, text) for text in translated_texts
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    safe_results = []
    for r in results:
        if isinstance(r, Exception):
            safe_results.append([])
        else:
            safe_results.append(r)

    return safe_results
