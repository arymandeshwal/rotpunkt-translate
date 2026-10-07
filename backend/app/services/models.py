from dataclasses import dataclass


@dataclass
class GlossaryTermInfo:
    entry_id: int
    source_text: str
    target_text: str
    is_dnt: bool
    is_case_sensitive: bool
