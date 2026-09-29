import io
import os
import zipfile
from typing import BinaryIO

from app.services.parsing.cleaner import clean_text
from app.services.parsing.docx import MAX_DOCX_SIZE_BYTES, extract_text_from_docx
from app.services.parsing.exceptions import UnsupportedFormatError
from app.services.parsing.pdf import MAX_PDF_SIZE_BYTES, extract_text_from_pdf

DEFAULT_MAX_SIZE_BYTES = max(MAX_PDF_SIZE_BYTES, MAX_DOCX_SIZE_BYTES)

PDF_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
}

DOCX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/docx",
    "application/msword",
}


def is_pdf_bytes(data: bytes) -> bool:
    """Check if the byte buffer begins with PDF magic bytes."""
    return b"%PDF-" in data[:1024]


def is_docx_bytes(data: bytes) -> bool:
    """Check if the byte buffer is a valid DOCX (ZIP archive containing word/)."""
    if not data.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return any(name.startswith("word/") for name in zf.namelist())
    except Exception:
        return False


def detect_format(
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> str:
    """Detect whether document data is 'pdf' or 'docx'.

    Inspection order:
        1. Magic byte sniffing (PDF header / DOCX zip structure)
        2. Declared Content-Type header
        3. Filename extension

    Returns:
        'pdf' or 'docx'

    Raises:
        UnsupportedFormatError: If format cannot be determined or is unsupported.
    """
    # 1. Magic byte sniffing
    if is_pdf_bytes(data):
        return "pdf"
    if is_docx_bytes(data):
        return "docx"

    # 2. Content-Type inspection
    if content_type:
        clean_ct = content_type.split(";")[0].strip().lower()
        if clean_ct in PDF_MIME_TYPES:
            return "pdf"
        if clean_ct in DOCX_MIME_TYPES:
            return "docx"

    # 3. Filename extension inspection
    if filename:
        _, ext = os.path.splitext(filename.lower())
        if ext == ".pdf":
            return "pdf"
        if ext in (".docx", ".doc"):
            return "docx"

    hint = f"filename='{filename}', content_type='{content_type}'"
    raise UnsupportedFormatError(
        f"Unsupported or unrecognized document format ({hint}). "
        f"Supported formats: PDF, DOCX."
    )


def parse_document(
    source: bytes | BinaryIO,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    clean: bool = True,
    max_size: int = DEFAULT_MAX_SIZE_BYTES,
) -> str:
    """Parse document bytes or stream to plain text with format auto-detection.

    Args:
        source: Raw document bytes or readable binary stream.
        filename: Optional filename for extension hints.
        content_type: Optional MIME content type.
        clean: Whether to apply clean_text pipeline (default True).
        max_size: Maximum allowed file size in bytes.

    Returns:
        Extracted (and optionally cleaned) plain text.

    Raises:
        UnsupportedFormatError: If format is not PDF or DOCX.
        ParsingError: If extraction fails or file limits are exceeded.
    """
    raw_bytes = source if isinstance(source, bytes) else source.read()

    doc_format = detect_format(
        raw_bytes,
        filename=filename,
        content_type=content_type,
    )

    if doc_format == "pdf":
        text = extract_text_from_pdf(raw_bytes, max_size=max_size)
    elif doc_format == "docx":
        text = extract_text_from_docx(raw_bytes, max_size=max_size)
    else:
        raise UnsupportedFormatError(
            f"Handler for format '{doc_format}' not configured"
        )

    if clean:
        text = clean_text(text)

    return text
