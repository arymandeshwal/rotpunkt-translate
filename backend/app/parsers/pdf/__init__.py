from app.parsers.pdf.extract import ExtractedDocument, ExtractedPage, TextLine, extract
from app.parsers.pdf.layout import (
    PageInfo,
    ParsedDocument,
    Segment,
    SegmentKind,
    build_segments,
)


def parse_pdf(pdf: bytes) -> ParsedDocument:
    """PDF bytes -> segments (headings, paragraphs, list items) in reading order."""
    return build_segments(extract(pdf))


__all__ = [
    "ExtractedDocument",
    "ExtractedPage",
    "PageInfo",
    "ParsedDocument",
    "Segment",
    "SegmentKind",
    "TextLine",
    "build_segments",
    "extract",
    "parse_pdf",
]
