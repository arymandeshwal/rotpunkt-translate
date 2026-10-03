"""Development and demo seed data.

Terms come from Rotpunkt's public multilingual documents (see samples/SOURCES.md).
Gaps (e.g. most French and Dutch terms) are intentional: they are unverified, and they
exercise the glossary's "missing translation" view.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.glossary import GlossaryEntryCreate, TermIn
from app.services import glossary as glossary_service

GLOSSARY_SEED_FILE = Path(__file__).with_name("glossary.json")


@dataclass
class SeedResult:
    created: int = 0
    skipped: list[str] = field(default_factory=list)


def load_glossary_seed(path: Path = GLOSSARY_SEED_FILE) -> list[GlossaryEntryCreate]:
    """Parse the seed file; terms are stored as {language: text} for readability."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    for item in raw:
        item["terms"] = [TermIn(language=lang, text=text) for lang, text in item["terms"].items()]
    return TypeAdapter(list[GlossaryEntryCreate]).validate_python(raw)


async def seed_glossary(session: AsyncSession, entries: list[GlossaryEntryCreate]) -> SeedResult:
    """Create entries whose terms are all new; never modify existing entries."""
    result = SeedResult()
    for entry in entries:
        try:
            await glossary_service.create_entry(session, entry)
            result.created += 1
        except glossary_service.DuplicateTermsError:
            result.skipped.append(entry.terms[0].text)
    return result
