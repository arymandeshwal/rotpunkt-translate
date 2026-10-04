"""Turn extracted lines into segments (headings, paragraphs, list items) in reading order.

Pipeline per page:
  1. merge fragments  – pieces of one visual line stored separately ("Drawer Solutions" + "®")
  2. mark list items  – lines starting with a bullet glyph or next to a drawn checkbox/bullet
  3. group paragraphs – consecutive lines with the same style, small gap and same alignment
  4. reading order    – recursive XY-cut: columns left to right, each top to bottom
  5. classify         – heading, list item or paragraph

All thresholds are relative to the font size, so they work for 7pt flyers and 40pt titles.
"""

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from app.parsers.pdf.extract import BBox, ExtractedDocument, ExtractedPage
from app.parsers.pdf.text import REPLACEMENT_CHARACTER, UNREADABLE_WARNING

SegmentKind = Literal["heading", "paragraph", "list_item"]

# Thresholds, in multiples of the font size unless noted.
FRAGMENT_MAX_GAP = 1.0  # horizontal gap between pieces of one visual line
FRAGMENT_SPACE_GAP = 0.15  # pieces further apart than this are joined with a space
PARAGRAPH_MAX_GAP = 0.8  # vertical gap between lines of one paragraph
PARAGRAPH_MAX_OVERLAP = 0.5  # lines may overlap vertically this much (tight leading)
INDENT_TOLERANCE = 1.5  # left edges this close count as aligned
MARKER_MAX_DISTANCE = 3.0  # a checkbox/bullet this close to the left of a line marks it
COLUMN_MIN_GAP = 4.0  # points; narrower vertical gaps are not column gutters
SIZE_TOLERANCE = 0.6  # points; sizes this close count as the same style
HEADING_SIZE_RATIO = 1.25  # this much larger than body text makes a heading
HEADING_MAX_LINES = 2
HEADING_MAX_WORDS = 12

# A bullet glyph at the start of a line. An unmapped glyph (U+FFFD) only counts when followed
# by an uppercase letter, a digit or a space; "�bersicht" is more likely a lost "Ü".
_BULLET = re.compile(r"^\s*(?:[•●▪■◦‣∙○□☐-]\s*|�(?=\s|[A-ZÄÖÜ0-9])\s*)(?=\S)")


@dataclass
class Segment:
    order: int
    """Position in the document's reading order, starting at 0."""
    page: int
    kind: SegmentKind
    text: str
    bbox: BBox
    font_size: float
    bold: bool
    warnings: set[str] = field(default_factory=set)


@dataclass
class PageInfo:
    number: int
    width: float
    height: float


@dataclass
class ParsedDocument:
    pages: list[PageInfo]
    segments: list[Segment]


@dataclass
class _Line:
    text: str
    bbox: BBox
    font_size: float
    bold: bool
    warnings: set[str]
    starts_list_item: bool = False

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]


@dataclass
class _Paragraph:
    lines: list[_Line]

    @property
    def bbox(self) -> BBox:
        return _union(line.bbox for line in self.lines)


# --- geometry ------------------------------------------------------------------------------


def _union(boxes: Iterable[BBox]) -> BBox:
    items = list(boxes)
    return (
        min(b[0] for b in items),
        min(b[1] for b in items),
        max(b[2] for b in items),
        max(b[3] for b in items),
    )


def _vertical_overlap(a: BBox, b: BBox) -> float:
    return max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _horizontal_overlap(a: BBox, b: BBox) -> float:
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0]))


def _same_row(a: BBox, b: BBox) -> bool:
    smaller = min(a[3] - a[1], b[3] - b[1])
    return smaller > 0 and _vertical_overlap(a, b) >= 0.5 * smaller


# --- 1. fragments --------------------------------------------------------------------------


def _merge_fragments(lines: list[_Line]) -> list[_Line]:
    merged: list[_Line] = []
    for line in sorted(lines, key=lambda item: item.bbox[0]):
        for target in merged:
            size = max(target.font_size, line.font_size)
            gap = line.bbox[0] - target.bbox[2]
            if _same_row(target.bbox, line.bbox) and -1 <= gap <= FRAGMENT_MAX_GAP * size:
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


def _mark_list_items(lines: list[_Line], markers: list[BBox]) -> None:
    for line in lines:
        bullet = _BULLET.match(line.text)
        if bullet:
            line.text = line.text[bullet.end() :]
            line.starts_list_item = True
            if REPLACEMENT_CHARACTER not in line.text:
                line.warnings.discard(UNREADABLE_WARNING)
            continue
        for marker in markers:
            distance = line.bbox[0] - marker[2]
            if (
                _same_row(marker, line.bbox)
                and -1 <= distance <= MARKER_MAX_DISTANCE * line.font_size
            ):
                line.starts_list_item = True
                break


# --- 3. paragraphs -------------------------------------------------------------------------


def _same_style(a: _Line, b: _Line) -> bool:
    return abs(a.font_size - b.font_size) <= SIZE_TOLERANCE and a.bold == b.bold


def _aligned(previous: _Line, line: _Line) -> bool:
    narrower = min(previous.width, line.width)
    left_aligned = abs(previous.bbox[0] - line.bbox[0]) <= INDENT_TOLERANCE * line.font_size
    overlapping = _horizontal_overlap(previous.bbox, line.bbox) >= 0.5 * narrower
    return left_aligned or overlapping


def _continues(paragraph: _Paragraph, line: _Line) -> float | None:
    """The vertical gap if `line` continues `paragraph`, otherwise None."""
    if line.starts_list_item:
        return None
    previous = paragraph.lines[-1]
    gap = line.bbox[1] - previous.bbox[3]
    size = line.font_size
    if not -PARAGRAPH_MAX_OVERLAP * size <= gap <= PARAGRAPH_MAX_GAP * size:
        return None
    if not _same_style(previous, line) or not _aligned(previous, line):
        return None
    return gap


def _group_paragraphs(lines: list[_Line]) -> list[_Paragraph]:
    paragraphs: list[_Paragraph] = []
    for line in sorted(lines, key=lambda item: (item.bbox[1], item.bbox[0])):
        candidates = [
            (gap, paragraph)
            for paragraph in paragraphs
            if (gap := _continues(paragraph, line)) is not None
        ]
        if candidates:
            min(candidates, key=lambda c: c[0])[1].lines.append(line)
        else:
            paragraphs.append(_Paragraph([line]))
    return paragraphs


# --- 4. reading order ----------------------------------------------------------------------


def _widest_gap(spans: list[tuple[float, float]]) -> tuple[float, float] | None:
    """(position, width) of the widest empty stretch between the intervals, if any."""
    ordered = sorted(spans)
    reach = ordered[0][1]
    best: tuple[float, float] | None = None
    for start, end in ordered[1:]:
        width = start - reach
        if width >= 0 and (best is None or width > best[1]):
            best = ((reach + start) / 2, width)
        reach = max(reach, end)
    return best


def _reading_order(paragraphs: list[_Paragraph]) -> list[_Paragraph]:
    """Recursive XY-cut: split along the widest empty band, vertical (columns, left to right)
    or horizontal (top to bottom), until every part is a single paragraph.

    Taking the widest gap separates headers and footers before columns (they sit far above
    or below), and keeps columns intact when their paragraph breaks happen to line up."""
    if len(paragraphs) <= 1:
        return paragraphs
    boxes = [(p, p.bbox) for p in paragraphs]
    gutter = _widest_gap([(b[0], b[2]) for _, b in boxes])
    band = _widest_gap([(b[1], b[3]) for _, b in boxes])

    if gutter and gutter[1] >= COLUMN_MIN_GAP and (band is None or gutter[1] >= band[1]):
        left = [p for p, b in boxes if b[2] <= gutter[0]]
        right = [p for p, b in boxes if b[2] > gutter[0]]
        return _reading_order(left) + _reading_order(right)
    if band:
        top = [p for p, b in boxes if b[3] <= band[0]]
        bottom = [p for p, b in boxes if b[3] > band[0]]
        return _reading_order(top) + _reading_order(bottom)

    # Overlapping boxes cannot be cut: fall back to top-to-bottom, left-to-right.
    return sorted(paragraphs, key=lambda p: (p.bbox[1], p.bbox[0]))


# --- 5. classification ---------------------------------------------------------------------


def _body_font_size(document: ExtractedDocument) -> float:
    """The font size covering the most characters in the document."""
    sizes: Counter[float] = Counter()
    for page in document.pages:
        for line in page.lines:
            sizes[line.font_size] += len(line.text)
    return sizes.most_common(1)[0][0] if sizes else 0.0


def _classify(paragraph: _Paragraph, text: str, body_size: float) -> SegmentKind:
    first = paragraph.lines[0]
    if first.starts_list_item:
        return "list_item"
    if body_size and first.font_size >= HEADING_SIZE_RATIO * body_size:
        return "heading"
    short = len(paragraph.lines) <= HEADING_MAX_LINES and len(text.split()) <= HEADING_MAX_WORDS
    if first.bold and short and not text.endswith((".", ",", ";")):
        return "heading"
    return "paragraph"


# --- public --------------------------------------------------------------------------------


def _page_paragraphs(page: ExtractedPage) -> list[_Paragraph]:
    lines = [
        _Line(line.text, line.bbox, line.font_size, line.bold, set(line.warnings))
        for line in page.lines
    ]
    lines = _merge_fragments(lines)
    _mark_list_items(lines, page.markers)
    return _reading_order(_group_paragraphs(lines))


def build_segments(document: ExtractedDocument) -> ParsedDocument:
    body_size = _body_font_size(document)
    segments: list[Segment] = []
    for page in document.pages:
        for paragraph in _page_paragraphs(page):
            # Lines are joined with a space; hyphenation is left to the translator.
            text = " ".join(part for line in paragraph.lines if (part := line.text.strip()))
            if not text:
                continue
            first = paragraph.lines[0]
            segments.append(
                Segment(
                    order=len(segments),
                    page=page.number,
                    kind=_classify(paragraph, text, body_size),
                    text=text,
                    bbox=paragraph.bbox,
                    font_size=first.font_size,
                    bold=first.bold,
                    warnings=set().union(*(line.warnings for line in paragraph.lines)),
                )
            )
    pages = [PageInfo(p.number, p.width, p.height) for p in document.pages]
    return ParsedDocument(pages=pages, segments=segments)
