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
# PyMuPDF sometimes puts text of very different sizes on one line (HPL cover: a 7 pt label next
# to a 33 pt title). Spans whose sizes differ by this factor become separate lines.
SIZE_SPLIT_RATIO = 1.5
# Spans this short ("®", "™") stay on their neighbour's line whatever their size.
TINY_SPAN = 2

Span = dict[str, Any]


@dataclass
class TextLine:
    """One line of text as found in the PDF.

    Attributes:
        text: Normalized text (see normalize_text).
        raw_text: The text exactly as stored in the PDF.
        bbox: Bounding box (x0, y0, x1, y1) in PDF points, origin top left.
        font_size: The font size covering most characters, rounded to 0.1 pt.
        bold: Whether most characters are bold.
        warnings: Problems found in the text, e.g. unreadable characters.
    """

    text: str
    raw_text: str
    bbox: BBox
    font_size: float
    bold: bool
    warnings: set[str] = field(default_factory=set)


@dataclass
class ExtractedPage:
    """All text lines and possible list markers of one page.

    Attributes:
        number: 1-based page number.
        width: Page width in PDF points.
        height: Page height in PDF points.
        lines: Text lines in the order PyMuPDF returns them (not reading order).
        markers: Bounding boxes of small drawn shapes (checkboxes, bullet dots) that may mark
            list items; the layout step decides whether they do.
    """

    number: int
    width: float
    height: float
    lines: list[TextLine]
    markers: list[BBox] = field(default_factory=list)


@dataclass
class ExtractedDocument:
    """The extraction result for a whole PDF.

    Attributes:
        pages: Every page, including pages without text.
    """

    pages: list[ExtractedPage]

    @property
    def text(self) -> str:
        """All normalized text, one line per text line, page after page."""
        return "\n".join(line.text for page in self.pages for line in page.lines)


def _is_bold(span: Span) -> bool:
    """Check whether a span is set in a bold font.

    Args:
        span: A PyMuPDF text span.

    Returns:
        True if the bold flag is set or the font name contains "bold".
    """
    return bool(span["flags"] & pymupdf.TEXT_FONT_BOLD) or "bold" in span["font"].lower()


def _style(spans: list[Span]) -> tuple[float, bool]:
    """Find the font size and boldness that cover most characters of some spans.

    Args:
        spans: Non-empty PyMuPDF spans.

    Returns:
        (font size rounded to 0.1 pt, whether more than half the characters are bold).
    """
    sizes: Counter[float] = Counter()
    bold_chars = 0
    for span in spans:
        length = len(span["text"])
        sizes[round(span["size"], 1)] += length
        if _is_bold(span):
            bold_chars += length
    total = sum(sizes.values())
    return sizes.most_common(1)[0][0], bold_chars * 2 > total


def _split_by_size(spans: list[Span]) -> list[list[Span]]:
    """Split a PyMuPDF line where the font size changes sharply.

    Args:
        spans: The non-empty spans of one PyMuPDF line, left to right.

    Returns:
        Groups of consecutive spans; a new group starts when a span's size differs from the
        last visible span's size by SIZE_SPLIT_RATIO or more. Whitespace spans are compared
        with nothing, and tiny spans (see TINY_SPAN) never start or end a group.
    """
    groups: list[list[Span]] = [[]]
    previous: Span | None = None  # last span with visible text
    for span in spans:
        visible = span["text"].strip()
        if visible and previous is not None:
            small, large = sorted((span["size"], previous["size"]))
            tiny = len(visible) <= TINY_SPAN or len(previous["text"].strip()) <= TINY_SPAN
            if large >= SIZE_SPLIT_RATIO * max(small, 1) and not tiny:
                groups.append([])
        groups[-1].append(span)
        if visible:
            previous = span
    return groups


def _to_line(spans: list[Span]) -> TextLine | None:
    """Build a TextLine from consecutive spans.

    Args:
        spans: Non-empty PyMuPDF spans of one visual line.

    Returns:
        The line, or None if it contains only whitespace (nothing to translate).
    """
    raw = "".join(span["text"] for span in spans)
    if not raw.strip():
        return None
    text, warnings = normalize_text(raw)
    # Style and position come from visible text only; PyMuPDF's whitespace spans can carry
    # the size of a neighbouring, much larger piece.
    visible = [span for span in spans if span["text"].strip()]
    font_size, bold = _style(visible)
    bbox: BBox = (
        min(span["bbox"][0] for span in visible),
        min(span["bbox"][1] for span in visible),
        max(span["bbox"][2] for span in visible),
        max(span["bbox"][3] for span in visible),
    )
    return TextLine(text, raw, bbox, font_size, bold, warnings)


def _markers(page: pymupdf.Page) -> list[BBox]:
    """Collect drawn shapes small enough to be a checkbox or bullet.

    Args:
        page: The PyMuPDF page.

    Returns:
        Bounding boxes of drawings between MARKER_MIN and MARKER_MAX points in both width
        and height. Rules, panels and specks are left out.
    """
    markers: list[BBox] = []
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if MARKER_MIN <= rect.width <= MARKER_MAX and MARKER_MIN <= rect.height <= MARKER_MAX:
            markers.append((rect.x0, rect.y0, rect.x1, rect.y1))
    return markers


def _extract_page(page: pymupdf.Page) -> ExtractedPage:
    """Extract the text lines and list markers of one page.

    Args:
        page: The PyMuPDF page.

    Returns:
        The page with all non-blank lines, including headers, footers and page numbers.
    """
    lines: list[TextLine] = []
    for block in page.get_text("dict", flags=EXTRACT_FLAGS)["blocks"]:
        if block["type"] != 0:  # image block
            continue
        for line in block["lines"]:
            spans = [span for span in line["spans"] if span["text"]]
            if not spans:
                continue
            for group in _split_by_size(spans):
                if (text_line := _to_line(group)) is not None:
                    lines.append(text_line)
    return ExtractedPage(
        number=page.number + 1,
        width=page.rect.width,
        height=page.rect.height,
        lines=lines,
        markers=_markers(page),
    )


def extract(pdf: bytes) -> ExtractedDocument:
    """Extract all text lines and possible list markers from a PDF.

    Args:
        pdf: The PDF file's content.

    Returns:
        One ExtractedPage per page, in page order.

    Raises:
        pymupdf.FileDataError: If the data is not a readable PDF.
    """
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        return ExtractedDocument(pages=[_extract_page(page) for page in doc])
