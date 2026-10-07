import re
from typing import Any

from app.services.models import GlossaryTermInfo


def compute_deterministic_annotations(
    translated_text: str, glossary_infos: list[GlossaryTermInfo]
) -> list[dict[str, Any]]:
    """
    Find occurrences of glossary terms and DNT terms in the translated text.

    Args:
        translated_text: The output from the translation provider.
        glossary_infos: The rich glossary information for the language pair.

    Returns:
        A list of annotation dictionaries suitable for the 'annotations' JSON column.
    """
    annotations = []

    # Sort by length descending to match longest terms first (e.g., "Rotpunkt Küchen" before "Rotpunkt")
    # This prevents overlapping highlights if a short term is a substring of a long term.
    sorted_infos = sorted(glossary_infos, key=lambda x: len(x.target_text), reverse=True)

    # We need to keep track of matched intervals to prevent overlaps.
    matched_intervals = []

    def is_overlapping(start: int, end: int) -> bool:
        return any(start < m_end and end > m_start for m_start, m_end in matched_intervals)

    for info in sorted_infos:
        target = info.target_text
        if not target:
            continue

        flags = 0 if info.is_case_sensitive else re.IGNORECASE

        # We need a robust word boundary approach. For kitchen terms with hyphens (e.g. "Anti-Fingerprint"),
        # standard \b works if surrounded by space, but \b fails on things like "H203" if it's next to
        # a hyphen. Using a more permissive boundary: lookarounds for non-word chars.
        # But let's start with standard \b. If it fails on some, we can improve it.
        pattern = rf"\b{re.escape(target)}\b"

        for match in re.finditer(pattern, translated_text, flags=flags):
            start, end = match.span()

            if not is_overlapping(start, end):
                matched_intervals.append((start, end))
                annotations.append(
                    {
                        "start": start,
                        "end": end,
                        "type": "dnt" if info.is_dnt else "glossary",
                        "term_id": info.entry_id,
                        "text": match.group(0),
                    }
                )

    # Sort annotations by their start index to keep them in reading order
    annotations.sort(key=lambda x: x["start"])
    return annotations
