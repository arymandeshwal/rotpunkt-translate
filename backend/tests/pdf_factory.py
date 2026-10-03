"""Build small PDFs for parser tests, so no binary fixtures need to be committed."""

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
    size: float = 11
    bold: bool = False


def make_pdf(*pages: list[Text], width: float = 595, height: float = 842) -> bytes:
    """One list of Text items per page; an empty list makes a blank page."""
    doc = pymupdf.open()
    for items in pages:
        page = doc.new_page(width=width, height=height)
        for name in (REGULAR, BOLD):
            page.insert_font(fontname=name, fontbuffer=pymupdf.Font(name).buffer)
        for item in items:
            page.insert_text(
                (item.x, item.y),
                item.text,
                fontname=BOLD if item.bold else REGULAR,
                fontsize=item.size,
            )
    pdf: bytes = doc.tobytes()
    doc.close()
    return pdf
