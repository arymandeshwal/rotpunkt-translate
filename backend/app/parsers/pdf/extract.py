"""Extract every line of text from a PDF, with its position and font information."""

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import pymupdf

from app.parsers.pdf.text import normalize_text

# Keep whitespace as is, ignore text outside the visible page; ligatures (ﬁ) come out as "fi".
# No dehyphenation: line breaks are handled by the translation engine.
EXTRACT_FLAGS = pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_MEDIABOX_CLIP

BBox = tuple[float, float, float, float]

# Size range (points) of drawn shapes kept as possible checkboxes or bullets.
MARKER_MIN = 2.0
MARKER_MAX = 40.0


@dataclass
class TextLine:
    text: str
    """Normalized text (see normalize_text)."""
    raw_text: str
    """Exactly as stored in the PDF."""
    bbox: BBox
    """x0, y0, x1, y1 in PDF points, origin top left."""
    font_size: float
    bold: bool
    block_no: int
    """PyMuPDF's block number; a grouping hint for layout analysis."""
    warnings: set[str] = field(default_factory=set)


@dataclass
class ExtractedPage:
    number: int
    """1-based."""
    width: float
    height: float
    lines: list[TextLine]
    markers: list[BBox] = field(default_factory=list)
    """Small drawn shapes (checkboxes, bullet dots) that may mark list items."""


@dataclass
class ExtractedDocument:
    pages: list[ExtractedPage]

    @property
    def text(self) -> str:
        return "\n".join(line.text for page in self.pages for line in page.lines)


def _is_bold(span: dict[str, Any]) -> bool:
    return bool(span["flags"] & pymupdf.TEXT_FONT_BOLD) or "bold" in span["font"].lower()


def _line_style(spans: list[dict[str, Any]]) -> tuple[float, bool]:
    """Font size and boldness that cover most characters of the line."""
    sizes: Counter[float] = Counter()
    bold_chars = 0
    for span in spans:
        length = len(span["text"])
        sizes[round(span["size"], 1)] += length
        if _is_bold(span):
            bold_chars += length
    total = sum(sizes.values())
    return sizes.most_common(1)[0][0], bold_chars * 2 > total


def _extract_page(page: pymupdf.Page) -> ExtractedPage:
    lines: list[TextLine] = []
    data = page.get_text("dict", flags=EXTRACT_FLAGS)
    for block in data["blocks"]:
        if block["type"] != 0:  # images
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"]]
            raw = "".join(s["text"] for s in spans)
            if not raw.strip():
                continue
            text, warnings = normalize_text(raw)
            font_size, bold = _line_style(spans)
            lines.append(
                TextLine(
                    text=text,
                    raw_text=raw,
                    bbox=tuple(line["bbox"]),
                    font_size=font_size,
                    bold=bold,
                    block_no=block["number"],
                    warnings=warnings,
                )
            )
    return ExtractedPage(
        number=page.number + 1,
        width=page.rect.width,
        height=page.rect.height,
        lines=lines,
        markers=_markers(page),
    )


def _markers(page: pymupdf.Page) -> list[BBox]:
    """Drawn shapes small enough to be a checkbox or bullet; layout decides if they are one."""
    markers: list[BBox] = []
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if MARKER_MIN <= rect.width <= MARKER_MAX and MARKER_MIN <= rect.height <= MARKER_MAX:
            markers.append((rect.x0, rect.y0, rect.x1, rect.y1))
    return markers


def extract(pdf: bytes) -> ExtractedDocument:
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        return ExtractedDocument(pages=[_extract_page(page) for page in doc])
