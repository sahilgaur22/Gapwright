import io
import logging
from typing import BinaryIO

import pdfplumber
import pypdf

from app.services.parsing.exceptions import (
    EmptyPDFError,
    PDFPageLimitExceededError,
    PDFParsingError,
    PDFSizeLimitExceededError,
)

logger = logging.getLogger(__name__)

MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_PDF_PAGES = 100


def extract_text_from_pdf(
    source: bytes | BinaryIO,
    *,
    max_pages: int = MAX_PDF_PAGES,
    max_size: int = MAX_PDF_SIZE_BYTES,
) -> str:
    """Extract plain text from PDF bytes or stream using pdfplumber with a
    pypdf fallback.

    Args:
        source: Raw PDF bytes or file-like binary stream.
        max_pages: Maximum permitted number of pages.
        max_size: Maximum permitted file size in bytes.

    Returns:
        Cleaned, extracted text string.

    Raises:
        PDFSizeLimitExceededError: If the PDF exceeds max_size.
        PDFPageLimitExceededError: If the PDF exceeds max_pages.
        EmptyPDFError: If no extractable text was found.
        PDFParsingError: If parsing fails and cannot be recovered.
    """
    if isinstance(source, bytes):
        if len(source) > max_size:
            raise PDFSizeLimitExceededError(
                f"PDF size ({len(source)} bytes) exceeds limit of {max_size} bytes"
            )
        pdf_bytes = source
    else:
        pdf_bytes = source.read()
        if len(pdf_bytes) > max_size:
            raise PDFSizeLimitExceededError(
                f"PDF size ({len(pdf_bytes)} bytes) exceeds limit of {max_size} bytes"
            )

    if not pdf_bytes:
        raise EmptyPDFError("PDF source is empty")

    # 1. Primary parser: pdfplumber
    extracted_pages: list[str] = []
    use_fallback = False

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)
            if page_count > max_pages:
                raise PDFPageLimitExceededError(
                    f"PDF page count ({page_count}) exceeds limit of {max_pages} pages"
                )

            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text.strip())
    except PDFPageLimitExceededError:
        raise
    except Exception as exc:
        logger.warning(
            f"pdfplumber extraction failed, attempting pypdf fallback: {exc}"
        )
        use_fallback = True

    # 2. Fallback parser: pypdf (if pdfplumber failed or returned no text)
    if use_fallback or not extracted_pages:
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            page_count = len(reader.pages)
            if page_count > max_pages:
                raise PDFPageLimitExceededError(
                    f"PDF page count ({page_count}) exceeds limit of {max_pages} pages"
                )

            extracted_pages = []
            for pypdf_page in reader.pages:
                text = pypdf_page.extract_text()
                if text:
                    extracted_pages.append(text.strip())
        except PDFPageLimitExceededError:
            raise
        except Exception as exc:
            raise PDFParsingError(f"Failed to parse PDF document: {exc}") from exc

    full_text = "\n\n".join(filter(None, extracted_pages)).strip()
    if not full_text:
        raise EmptyPDFError("The PDF document does not contain any extractable text")

    return full_text
