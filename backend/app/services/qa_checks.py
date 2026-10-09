import re
from typing import Any

from app.services.models import GlossaryTermInfo


def compute_qa_issues(
    source_text: str,
    target_text: str,
    glossary_infos: list[GlossaryTermInfo],
    is_translatable: bool,
) -> list[dict[str, Any]]:
    """
    Run automated QA checks on a translated segment.

    Args:
        source_text: The original text.
        target_text: The translated text.
        glossary_infos: Master glossary for the source -> target language pair.
        is_translatable: Whether the segment was considered translatable.

    Returns:
        A list of issue dictionaries suitable for the 'issues' JSON column.
    """
    issues = []

    if not is_translatable:
        return issues

    source_stripped = source_text.strip()
    target_stripped = target_text.strip()

    # Check I1: Untranslated text
    if not target_stripped:
        issues.append(
            {
                "type": "untranslated",
                "message": "Translation is completely empty.",
                "severity": "error",
            }
        )
    elif source_stripped and source_stripped == target_stripped:
        # Ignore very short segments like single characters, numbers or punctuation
        # which might validly be identical in both languages
        if len(source_stripped) > 3 and any(c.isalpha() for c in source_stripped):
            issues.append(
                {
                    "type": "untranslated",
                    "message": "Translation is identical to the source text.",
                    "severity": "warning",
                }
            )

    # Check I2: Missing glossary terms
    # Sort descending by length just in case
    sorted_infos = sorted(glossary_infos, key=lambda x: len(x.source_text), reverse=True)

    for info in sorted_infos:
        # Does the source term exist in the source text?
        source_flags = 0 if info.is_case_sensitive else re.IGNORECASE
        source_pattern = rf"\b{re.escape(info.source_text)}\b"

        if re.search(source_pattern, source_text, flags=source_flags):
            # The term is in the source text!
            # Did they use the target term?
            expected_target = info.target_text if not info.is_dnt else info.source_text
            if not expected_target:
                continue

            target_flags = 0 if info.is_case_sensitive else re.IGNORECASE
            target_pattern = rf"\b{re.escape(expected_target)}\b"

            if not re.search(target_pattern, target_text, flags=target_flags):
                issues.append(
                    {
                        "type": "missing_term",
                        "term": info.source_text,
                        "expected": expected_target,
                        "message": f"Glossary term '{info.source_text}' found in source, but expected translation '{expected_target}' is missing.",
                        "severity": "warning",
                    }
                )

    return issues
