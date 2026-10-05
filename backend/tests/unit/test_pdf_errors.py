import pymupdf
import pytest

from app.parsers.pdf import (
    NO_TEXT_LAYER_WARNING,
    EncryptedPdfError,
    InvalidPdfError,
    NoTextError,
    PdfError,
    TooLargeError,
    parse_pdf,
)
from app.parsers.pdf import errors as pdf_errors
from tests.pdf_factory import Image, Text, make_pdf

TEXT_PDF = make_pdf([Text("Pflegehinweise für Ihre Küche")])


def encrypt(pdf: bytes, **options: object) -> bytes:
    """Re-save a PDF with AES-256 encryption.

    Args:
        pdf: An unencrypted PDF.
        **options: Passed to pymupdf.Document.tobytes, e.g. user_pw and owner_pw.

    Returns:
        The encrypted PDF.
    """
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        # PyMuPDF defines its constants at runtime, invisible to mypy.
        aes_256 = pymupdf.PDF_ENCRYPT_AES_256  # type: ignore[attr-defined]
        encrypted: bytes = doc.tobytes(encryption=aes_256, **options)
    return encrypted


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"", "The file is empty."),
        (b"PK\x03\x04 a zip file, not a PDF", "The file is not a PDF or it is damaged."),
        (TEXT_PDF[: len(TEXT_PDF) // 3], "The file is not a PDF or it is damaged."),
    ],
    ids=["empty", "not-a-pdf", "truncated"],
)
def test_invalid_files_are_rejected(data: bytes, message: str) -> None:
    with pytest.raises(InvalidPdfError, match=message) as error:
        parse_pdf(data)

    assert error.value.code == "invalid_pdf"


def test_password_protected_pdf_is_rejected() -> None:
    pdf = encrypt(TEXT_PDF, user_pw="secret", owner_pw="owner")

    with pytest.raises(EncryptedPdfError, match="password-protected") as error:
        parse_pdf(pdf)

    assert error.value.code == "encrypted_pdf"


def test_pdf_with_only_permission_restrictions_is_accepted() -> None:
    # An owner password alone (e.g. "no printing") does not prevent reading the text.
    pdf = encrypt(TEXT_PDF, owner_pw="owner", permissions=0)

    assert [s.text for s in parse_pdf(pdf).segments] == ["Pflegehinweise für Ihre Küche"]


def test_file_over_the_size_limit_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.parsers.pdf.extract.MAX_FILE_BYTES", len(TEXT_PDF) - 1)

    with pytest.raises(TooLargeError, match="the limit is") as error:
        parse_pdf(TEXT_PDF)

    assert error.value.code == "too_large"


def test_pdf_over_the_page_limit_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.parsers.pdf.extract.MAX_PAGES", 2)
    pdf = make_pdf([Text("1")], [Text("2")], [Text("3")])

    with pytest.raises(TooLargeError, match="The PDF has 3 pages; the limit is 2."):
        parse_pdf(pdf)


def test_limits_fit_rotpunkts_documents() -> None:
    # The largest public Rotpunkt brochure is about 23 MB with fewer than 100 pages.
    assert pdf_errors.MAX_FILE_BYTES >= 50 * 1024 * 1024
    assert pdf_errors.MAX_PAGES >= 100


@pytest.mark.parametrize(
    "pages",
    [[[Image()]], [[Image()], [Image()]], [[]]],
    ids=["scanned-page", "scanned-document", "blank-page"],
)
def test_pdf_without_any_text_is_rejected(pages: list[list[Image]]) -> None:
    with pytest.raises(NoTextError, match="Scanned documents are not supported yet") as error:
        parse_pdf(make_pdf(*pages))

    assert error.value.code == "no_text"


def test_scanned_page_in_a_digital_pdf_is_flagged_not_rejected() -> None:
    document = parse_pdf(make_pdf([Text("Seite eins")], [Image()], [Text("Seite drei")]))

    assert [s.page for s in document.segments] == [1, 3]
    assert [p.warnings for p in document.pages] == [set(), {NO_TEXT_LAYER_WARNING}, set()]


def test_blank_page_is_not_flagged_as_scanned() -> None:
    document = parse_pdf(make_pdf([Text("Seite eins")], []))

    assert document.pages[1].warnings == set()


def test_pages_with_text_and_images_are_not_flagged() -> None:
    document = parse_pdf(make_pdf([Image(0, 0, 595, 400), Text("Bildunterschrift", y=450)]))

    assert document.pages[0].warnings == set()
    assert [s.text for s in document.segments] == ["Bildunterschrift"]


def test_all_errors_share_a_base_class_with_user_facing_messages() -> None:
    for error_type in (InvalidPdfError, EncryptedPdfError, TooLargeError, NoTextError):
        assert issubclass(error_type, PdfError)
