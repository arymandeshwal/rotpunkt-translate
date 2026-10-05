"""PDF parsing: parse_pdf() turns a PDF into translation segments in reading order."""

from app.parsers.pdf.errors import (
    EncryptedPdfError,
    InvalidPdfError,
    NoTextError,
    PdfError,
    TooLargeError,
)

# Imported under another name: binding "extract" here would hide the module of that name.
from app.parsers.pdf.extract import NO_TEXT_LAYER_WARNING, TextLine
from app.parsers.pdf.extract import extract as _extract
from app.parsers.pdf.layout import PageInfo, ParsedDocument, Segment, SegmentKind, build_segments


def parse_pdf(pdf: bytes) -> ParsedDocument:
    """Parse a PDF into segments (headings, paragraphs, list items) in reading order.

    Args:
        pdf: The PDF file's content.

    Returns:
        Page dimensions and warnings, and all segments in reading order.

    Raises:
        PdfError: A subclass explaining why the file cannot be parsed (invalid, encrypted,
            too large or without text); str(error) is a user-facing message.
    """
    return build_segments(_extract(pdf))


__all__ = [
    "NO_TEXT_LAYER_WARNING",
    "EncryptedPdfError",
    "InvalidPdfError",
    "NoTextError",
    "PageInfo",
    "ParsedDocument",
    "PdfError",
    "Segment",
    "SegmentKind",
    "TextLine",
    "TooLargeError",
    "parse_pdf",
]
