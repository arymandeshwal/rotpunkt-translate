"""Build small PDFs for parser tests, so no binary fixtures need to be committed."""

from collections.abc import Sequence
from dataclasses import dataclass

import pymupdf

# Noto Sans (from pymupdf-fonts) covers soft hyphens, thin spaces and combining marks,
# which the built-in base-14 fonts silently replace.
REGULAR = "notos"
BOLD = "notosbo"


@dataclass
class Text:
    text: str
    x: float = 72
    y: float = 72
    """Baseline."""
    size: float = 11
    bold: bool = False


@dataclass
class Box:
    """A drawn rectangle, e.g. a checkbox."""

    x0: float
    y0: float
    x1: float
    y1: float


def text_width(text: str, size: float = 11, bold: bool = False) -> float:
    width: float = pymupdf.Font(BOLD if bold else REGULAR).text_length(text, fontsize=size)
    return width


def paragraph(
    lines: list[str], x: float = 72, y: float = 72, size: float = 11, leading: float = 1.3
) -> list[Text]:
    """Consecutive lines with normal line spacing."""
    return [Text(line, x=x, y=y + i * size * leading, size=size) for i, line in enumerate(lines)]


def make_pdf(*pages: Sequence[Text | Box], width: float = 595, height: float = 842) -> bytes:
    """One list of items per page; an empty list makes a blank page."""
    doc = pymupdf.open()
    for items in pages:
        page = doc.new_page(width=width, height=height)
        for name in (REGULAR, BOLD):
            page.insert_font(fontname=name, fontbuffer=pymupdf.Font(name).buffer)
        for item in items:
            if isinstance(item, Box):
                page.draw_rect(pymupdf.Rect(item.x0, item.y0, item.x1, item.y1), width=0.5)
            else:
                page.insert_text(
                    (item.x, item.y),
                    item.text,
                    fontname=BOLD if item.bold else REGULAR,
                    fontsize=item.size,
                )
    pdf: bytes = doc.tobytes()
    doc.close()
    return pdf
