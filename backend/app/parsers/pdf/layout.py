"""Turn extracted lines into segments (headings, paragraphs, list items) in reading order.

Pipeline per page:
  1. merge fragments  – pieces of one visual line stored separately ("Drawer Solutions" + "®")
  2. mark list items  – lines starting with a bullet glyph or next to a drawn checkbox/bullet
  3. group paragraphs – consecutive lines with the same style, small gap and same alignment
  4. reading order    – recursive XY-cut: columns left to right, each top to bottom
  5. classify         – heading (by font size), list item or paragraph

Thresholds are multiples of the font size, so they work for 7 pt flyers and 60 pt titles.
Each value was checked against the public Rotpunkt sample documents (samples/SOURCES.md):
varying it within the noted range leaves the hand-verified results unchanged.
"""

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from app.parsers.pdf.extract import BBox, ExtractedDocument, ExtractedPage
from app.parsers.pdf.text import REPLACEMENT_CHARACTER, UNREADABLE_WARNING

SegmentKind = Literal["heading", "paragraph", "list_item"]

SAME_ROW_MIN_OVERLAP = 0.5  # share of the lower box height two boxes overlap on one row (0.1-0.5)
FRAGMENT_MAX_GAP = 1.0  # max horizontal gap between pieces of one visual line (0.25-2.0)
FRAGMENT_SPACE_GAP = 0.15  # wider gaps between pieces are joined with a space (0.05-0.6)
FRAGMENT_MAX_TINY = 2  # pieces this short ("®", "™") join a line of any font size
PARAGRAPH_MAX_GAP = 0.8  # max vertical gap between lines of one paragraph (0.7-1.0)
PARAGRAPH_MAX_OVERLAP = 0.5  # lines of a big title may overlap this much (0.25-1.0)
INDENT_TOLERANCE = 1.5  # left edges this close count as aligned (1.5-6.0)
ALIGN_MIN_OVERLAP = 0.5  # or: share of the narrower line two lines overlap (0.1-0.7)
MARKER_MAX_DISTANCE = 3.0  # max gap between a drawn checkbox/bullet and its line (1.0-12.0)
HEADING_SIZE_RATIO = 1.25  # font size relative to body text that makes a heading (1.15-1.25)

# A bullet glyph at the start of a line. An unmapped glyph (U+FFFD) only counts when followed
# by an uppercase letter, a digit or a space; "\ufffdbersicht" is more likely a lost "Ü".
_BULLET = re.compile(
    "^\\s*(?:[\u2022\u25cf\u25aa\u25a0\u25e6\u2023\u2219\u25cb\u25a1\u2610\ue000-\uf8ff]\\s*"
    "|\ufffd(?=\\s|[A-Z\u00c4\u00d6\u00dc0-9])\\s*)(?=\\S)"
)
# "DE – …", "EN – …": Rotpunkt prints translations of one text directly below each other.
_LANGUAGE_PREFIX = re.compile(r"^\s*(?:DE|EN|FR|NL|DA|NB|NO|ES|IT|PL|SV|CS)\s*[-\u2013]\s")


@dataclass
class Segment:
    """A unit of translation: one heading, paragraph or list item.

    Attributes:
        order: Position in the document's reading order, starting at 0.
        page: 1-based page number.
        kind: "heading", "paragraph" or "list_item".
        text: The segment's text; lines are joined with a space, bullets removed.
        bbox: Bounding box (x0, y0, x1, y1) in PDF points, origin top left.
        font_size: Font size of the first line.
        bold: Whether the first line is bold.
        warnings: Problems found in the text, e.g. unreadable characters.
    """

    order: int
    page: int
    kind: SegmentKind
    text: str
    bbox: BBox
    font_size: float
    bold: bool
    warnings: set[str] = field(default_factory=set)


@dataclass
class PageInfo:
    """Page dimensions, needed to place segments in a preview.

    Attributes:
        number: 1-based page number.
        width: Page width in PDF points.
        height: Page height in PDF points.
    """

    number: int
    width: float
    height: float


@dataclass
class ParsedDocument:
    """The result of parsing a PDF.

    Attributes:
        pages: Every page, including pages without text.
        segments: All segments in reading order across the whole document.
    """

    pages: list[PageInfo]
    segments: list[Segment]


@dataclass
class _Line:
    """A mutable working copy of an extracted line; merging and list marking change it.

    Attributes:
        text: Line text.
        bbox: Bounding box in PDF points.
        font_size: Dominant font size.
        bold: Whether most characters are bold.
        warnings: Problems found in the text.
        starts_list_item: Set when a bullet or drawn marker introduces the line.
    """

    text: str
    bbox: BBox
    font_size: float
    bold: bool
    warnings: set[str]
    starts_list_item: bool = False


Paragraph = list[_Line]


# --- geometry ------------------------------------------------------------------------------


def _union(boxes: Iterable[BBox]) -> BBox:
    """Return the smallest box containing all given boxes.

    Args:
        boxes: One or more bounding boxes.

    Returns:
        The enclosing bounding box.
    """
    items = list(boxes)
    return (
        min(b[0] for b in items),
        min(b[1] for b in items),
        max(b[2] for b in items),
        max(b[3] for b in items),
    )


def _same_row(a: BBox, b: BBox) -> bool:
    """Check whether two boxes sit on the same text row.

    Args:
        a: First bounding box.
        b: Second bounding box.

    Returns:
        True if they overlap vertically by at least SAME_ROW_MIN_OVERLAP of the lower box.
    """
    overlap = min(a[3], b[3]) - max(a[1], b[1])
    lower = min(a[3] - a[1], b[3] - b[1])
    return lower > 0 and overlap >= SAME_ROW_MIN_OVERLAP * lower


# --- 1. fragments --------------------------------------------------------------------------


def _merge_fragments(lines: list[_Line]) -> list[_Line]:
    """Join pieces of one visual line that the PDF stores as separate lines.

    Two pieces are joined when they share a row, are at most FRAGMENT_MAX_GAP apart and have
    the same font size; tiny pieces such as "®" join regardless of size. A small title next
    to a large one stays separate.

    Args:
        lines: Lines of one page, in any order.

    Returns:
        The merged lines. Merged lines keep the style of the longer piece.
    """
    merged: list[_Line] = []
    for line in sorted(lines, key=lambda item: item.bbox[0]):
        for target in merged:
            size = max(target.font_size, line.font_size)
            gap = line.bbox[0] - target.bbox[2]
            tiny = len(line.text.strip()) <= FRAGMENT_MAX_TINY
            if (
                _same_row(target.bbox, line.bbox)
                and -1 <= gap <= FRAGMENT_MAX_GAP * size
                and (tiny or target.font_size == line.font_size)
            ):
                separator = "" if gap <= FRAGMENT_SPACE_GAP * size else " "
                main = target if len(target.text) >= len(line.text) else line
                target.text = target.text.rstrip() + separator + line.text.lstrip()
                target.bbox = _union([target.bbox, line.bbox])
                target.font_size, target.bold = main.font_size, main.bold
                target.warnings |= line.warnings
                break
        else:
            merged.append(line)
    return merged


# --- 2. list items -------------------------------------------------------------------------


def _mark_list_items(lines: list[_Line], markers: list[BBox], body_size: float) -> None:
    """Flag lines that start a list item, and strip bullet glyphs from their text.

    A line starts a list item if it begins with a bullet glyph, or if a drawn shape
    (checkbox, dot) sits just to its left on the same row. Large text such as titles is
    never a list item, even next to a decorative shape.

    Args:
        lines: Lines of one page; modified in place.
        markers: Small drawn shapes on the page, from extraction.
        body_size: The document's body text size.
    """
    for line in lines:
        bullet = _BULLET.match(line.text)
        if bullet:
            line.text = line.text[bullet.end() :]
            line.starts_list_item = True
            if REPLACEMENT_CHARACTER not in line.text:
                line.warnings.discard(UNREADABLE_WARNING)
        elif line.font_size < HEADING_SIZE_RATIO * body_size and any(
            _same_row(marker, line.bbox)
            and -1 <= line.bbox[0] - marker[2] <= MARKER_MAX_DISTANCE * line.font_size
            for marker in markers
        ):
            line.starts_list_item = True


# --- 3. paragraphs -------------------------------------------------------------------------


def _starts_paragraph(line: _Line) -> bool:
    """Check whether a line always begins a new paragraph.

    Args:
        line: The line to check.

    Returns:
        True for list items and for lines starting with a language code ("EN – …").
    """
    return line.starts_list_item or bool(_LANGUAGE_PREFIX.match(line.text))


def _continues(paragraph: Paragraph, line: _Line) -> float | None:
    """Check whether `line` continues `paragraph`.

    It does when the line follows the paragraph's last line closely (at most
    PARAGRAPH_MAX_GAP below it), has the same font size and boldness, and is aligned with it:
    left edges within INDENT_TOLERANCE or overlapping by ALIGN_MIN_OVERLAP.

    Args:
        paragraph: Lines grouped so far, top to bottom.
        line: The candidate line, which lies below the paragraph's first line.

    Returns:
        The vertical gap to the paragraph's last line if the line continues it, else None.
    """
    previous = paragraph[-1]
    size = line.font_size
    gap = line.bbox[1] - previous.bbox[3]
    if not -PARAGRAPH_MAX_OVERLAP * size <= gap <= PARAGRAPH_MAX_GAP * size:
        return None
    if (previous.font_size, previous.bold) != (line.font_size, line.bold):
        return None
    overlap = min(previous.bbox[2], line.bbox[2]) - max(previous.bbox[0], line.bbox[0])
    narrower = min(previous.bbox[2] - previous.bbox[0], line.bbox[2] - line.bbox[0])
    left_aligned = abs(previous.bbox[0] - line.bbox[0]) <= INDENT_TOLERANCE * size
    if not left_aligned and overlap < ALIGN_MIN_OVERLAP * narrower:
        return None
    return gap


def _group_paragraphs(lines: list[_Line]) -> list[Paragraph]:
    """Group the lines of a page into paragraphs.

    Lines are visited top to bottom; each joins the paragraph it continues most closely
    (see _continues), or starts a new one.

    Args:
        lines: Lines of one page, after fragment merging and list marking.

    Returns:
        Paragraphs in no particular order, each a top-to-bottom list of lines.
    """
    paragraphs: list[Paragraph] = []
    for line in sorted(lines, key=lambda item: (item.bbox[1], item.bbox[0])):
        candidates = (
            []
            if _starts_paragraph(line)
            else [
                (gap, paragraph)
                for paragraph in paragraphs
                if (gap := _continues(paragraph, line)) is not None
            ]
        )
        if candidates:
            min(candidates, key=lambda candidate: candidate[0])[1].append(line)
        else:
            paragraphs.append([line])
    return paragraphs


# --- 4. reading order ----------------------------------------------------------------------


def _widest_gap(spans: list[tuple[float, float]]) -> tuple[float, float] | None:
    """Find the widest empty stretch between intervals on one axis.

    Args:
        spans: (start, end) intervals, e.g. the x-ranges of paragraph boxes.

    Returns:
        (position, width) of the widest gap, or None if the intervals leave no gap.
    """
    ordered = sorted(spans)
    reach = ordered[0][1]
    best: tuple[float, float] | None = None
    for start, end in ordered[1:]:
        width = start - reach
        if width >= 0 and (best is None or width > best[1]):
            best = ((reach + start) / 2, width)
        reach = max(reach, end)
    return best


def _reading_order(paragraphs: list[Paragraph]) -> list[Paragraph]:
    """Sort paragraphs into reading order with a recursive XY-cut.

    The paragraphs are split along the widest empty band, vertical (columns, read left to
    right) or horizontal (read top to bottom), until each part holds one paragraph. Taking
    the widest band cuts off headers and footers before columns and keeps columns intact
    even when their paragraph breaks line up.

    Args:
        paragraphs: The paragraphs of one page.

    Returns:
        The same paragraphs in reading order.
    """
    if len(paragraphs) <= 1:
        return paragraphs
    boxes = [(paragraph, _union(line.bbox for line in paragraph)) for paragraph in paragraphs]
    gutter = _widest_gap([(box[0], box[2]) for _, box in boxes])
    band = _widest_gap([(box[1], box[3]) for _, box in boxes])

    if gutter and (band is None or gutter[1] >= band[1]):
        left = [p for p, box in boxes if box[2] <= gutter[0]]
        right = [p for p, box in boxes if box[2] > gutter[0]]
        return _reading_order(left) + _reading_order(right)
    if band:
        top = [p for p, box in boxes if box[3] <= band[0]]
        bottom = [p for p, box in boxes if box[3] > band[0]]
        return _reading_order(top) + _reading_order(bottom)
    # Overlapping boxes cannot be cut: fall back to top-to-bottom, left-to-right.
    return [p for p, _ in sorted(boxes, key=lambda item: (item[1][1], item[1][0]))]


# --- 5. classification ---------------------------------------------------------------------


def _body_font_size(document: ExtractedDocument) -> float:
    """Find the font size of the document's body text.

    Args:
        document: The extracted document.

    Returns:
        The font size covering the most characters, or 0 for a document without text.
    """
    sizes: Counter[float] = Counter()
    for page in document.pages:
        for line in page.lines:
            sizes[line.font_size] += len(line.text)
    return sizes.most_common(1)[0][0] if sizes else 0.0


def _classify(paragraph: Paragraph, body_size: float) -> SegmentKind:
    """Decide what kind of segment a paragraph is.

    Args:
        paragraph: The paragraph's lines.
        body_size: The document's body text size.

    Returns:
        "list_item" if it starts with a bullet or marker, "heading" if its text is at least
        HEADING_SIZE_RATIO times the body size and contains letters (so page numbers are
        not headings), otherwise "paragraph".
    """
    first = paragraph[0]
    if first.starts_list_item:
        return "list_item"
    has_letters = any(char.isalpha() for line in paragraph for char in line.text)
    if has_letters and body_size and first.font_size >= HEADING_SIZE_RATIO * body_size:
        return "heading"
    return "paragraph"


# --- public --------------------------------------------------------------------------------


def _page_paragraphs(page: ExtractedPage, body_size: float) -> list[Paragraph]:
    """Run layout steps 1 to 4 for one page.

    Args:
        page: The extracted page.
        body_size: The document's body text size.

    Returns:
        The page's paragraphs in reading order.
    """
    lines = [
        _Line(line.text, line.bbox, line.font_size, line.bold, set(line.warnings))
        for line in page.lines
    ]
    lines = _merge_fragments(lines)
    _mark_list_items(lines, page.markers, body_size)
    return _reading_order(_group_paragraphs(lines))


def build_segments(document: ExtractedDocument) -> ParsedDocument:
    """Turn an extracted document into segments in reading order.

    Lines are joined with a space; hyphenation is left to the translation engine.

    Args:
        document: The output of extract().

    Returns:
        Page dimensions and all segments, numbered in reading order across pages.
    """
    body_size = _body_font_size(document)
    segments: list[Segment] = []
    for page in document.pages:
        for paragraph in _page_paragraphs(page, body_size):
            text = " ".join(part for line in paragraph if (part := line.text.strip()))
            if not text:
                continue
            first = paragraph[0]
            segments.append(
                Segment(
                    order=len(segments),
                    page=page.number,
                    kind=_classify(paragraph, body_size),
                    text=text,
                    bbox=_union(line.bbox for line in paragraph),
                    font_size=first.font_size,
                    bold=first.bold,
                    warnings=set().union(*(line.warnings for line in paragraph)),
                )
            )
    pages = [PageInfo(page.number, page.width, page.height) for page in document.pages]
    return ParsedDocument(pages=pages, segments=segments)
