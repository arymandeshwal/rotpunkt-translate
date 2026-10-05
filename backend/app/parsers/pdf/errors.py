"""Reasons a PDF cannot be parsed. Each message is meant to be shown to the user."""

MAX_FILE_BYTES = 100 * 1024 * 1024  # Rotpunkt's largest public brochure is about 23 MB
MAX_PAGES = 500


class PdfError(Exception):
    """Base class: the PDF cannot be parsed. str(error) is a user-facing message.

    Attributes:
        code: Stable machine-readable reason, e.g. for API responses and tests.
    """

    code = "invalid_pdf"


class InvalidPdfError(PdfError):
    """The file is empty, not a PDF, or damaged."""

    code = "invalid_pdf"


class EncryptedPdfError(PdfError):
    """The PDF needs a password to open."""

    code = "encrypted_pdf"


class TooLargeError(PdfError):
    """The file exceeds MAX_FILE_BYTES or MAX_PAGES."""

    code = "too_large"


class NoTextError(PdfError):
    """The PDF contains no extractable text, typically a scan."""

    code = "no_text"
