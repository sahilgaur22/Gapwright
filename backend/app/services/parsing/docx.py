import io
import logging
from typing import BinaryIO

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.services.parsing.exceptions import (
    DOCXParsingError,
    DOCXSizeLimitExceededError,
    EmptyDOCXError,
)

logger = logging.getLogger(__name__)

MAX_DOCX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _extract_table_text(table: Table) -> str:
    """Extract plain text from a docx Table, formatting rows and cells."""
    row_strings: list[str] = []
    for row in table.rows:
        cell_texts: list[str] = []
        for cell in row.cells:
            text = cell.text.strip()
            cell_texts.append(text)
        # Avoid duplicated row text when all cells are identical
        # but keep normal cells separated by tab
        row_line = "\t".join(cell_texts).strip()
        if row_line:
            row_strings.append(row_line)
    return "\n".join(row_strings)


def extract_text_from_docx(
    source: bytes | BinaryIO,
    *,
    max_size: int = MAX_DOCX_SIZE_BYTES,
) -> str:
    """Extract text from a DOCX document including paragraphs and tables in order.

    Args:
        source: Raw DOCX bytes or file-like binary stream.
        max_size: Maximum permitted file size in bytes.

    Returns:
        Cleaned text string from the DOCX document.

    Raises:
        DOCXSizeLimitExceededError: If the document exceeds max_size.
        EmptyDOCXError: If no extractable text was found.
        DOCXParsingError: If parsing fails or the document is invalid.
    """
    docx_bytes = source if isinstance(source, bytes) else source.read()

    if len(docx_bytes) > max_size:
        raise DOCXSizeLimitExceededError(
            f"DOCX size ({len(docx_bytes)} bytes) exceeds limit of {max_size} bytes"
        )

    if not docx_bytes:
        raise EmptyDOCXError("DOCX source is empty")

    try:
        doc = Document(io.BytesIO(docx_bytes))
    except Exception as exc:
        raise DOCXParsingError(f"Failed to open DOCX document: {exc}") from exc

    blocks: list[str] = []

    try:
        # Traverse elements in document order to keep paragraphs and tables interleaved
        for element in doc.element.body:
            tag = element.tag.lower()
            if tag.endswith("p"):
                para = Paragraph(element, doc)
                text = para.text.strip()
                if text:
                    blocks.append(text)
            elif tag.endswith("tbl"):
                tbl = Table(element, doc)
                tbl_text = _extract_table_text(tbl)
                if tbl_text:
                    blocks.append(tbl_text)
    except Exception as exc:
        logger.warning(
            f"Sequential traversal failed, falling back to separate extraction: {exc}"
        )
        blocks = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                blocks.append(text)
        for tbl in doc.tables:
            tbl_text = _extract_table_text(tbl)
            if tbl_text:
                blocks.append(tbl_text)

    full_text = "\n\n".join(blocks).strip()
    if not full_text:
        raise EmptyDOCXError("The DOCX document does not contain any extractable text")

    return full_text
