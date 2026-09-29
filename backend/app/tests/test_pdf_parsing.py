import io
from unittest.mock import patch

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, PageTemplate, Paragraph, SimpleDocTemplate

from app.services.parsing.pdf import (
    EmptyPDFError,
    PDFPageLimitExceededError,
    PDFParsingError,
    PDFSizeLimitExceededError,
    extract_text_from_pdf,
)


def generate_simple_text_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Course Title: Machine Learning and Deep Systems")
    c.drawString(100, 720, "Module 1: Supervised Learning, Logistic Regression")
    c.drawString(100, 690, "Module 2: Neural Networks, Transformers, LLMs")
    c.showPage()
    c.save()
    return buffer.getvalue()


def generate_multicolumn_pdf() -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Create two columns using frames
    frame1 = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width / 2 - 6, doc.height, id="col1"
    )
    frame2 = Frame(
        doc.leftMargin + doc.width / 2 + 6,
        doc.bottomMargin,
        doc.width / 2 - 6,
        doc.height,
        id="col2",
    )

    template = PageTemplate(id="two_col", frames=[frame1, frame2])
    doc.addPageTemplates([template])

    story = [
        Paragraph("Left Column: Data Structures and Algorithms.", styles["Normal"]),
        Paragraph(
            "Right Column: Cloud Computing and Kubernetes Architecture.",
            styles["Normal"],
        ),
    ]
    doc.build(story)
    return buffer.getvalue()


def generate_empty_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.showPage()
    c.save()
    return buffer.getvalue()


def generate_multipage_pdf(num_pages: int) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    for i in range(num_pages):
        c.drawString(100, 750, f"Page {i + 1} syllabus contents")
        c.showPage()
    c.save()
    return buffer.getvalue()


def test_extract_text_from_simple_pdf() -> None:
    pdf_bytes = generate_simple_text_pdf()
    text = extract_text_from_pdf(pdf_bytes)

    assert "Machine Learning and Deep Systems" in text
    assert "Supervised Learning" in text
    assert "Neural Networks, Transformers, LLMs" in text


def test_extract_text_from_multicolumn_pdf() -> None:
    pdf_bytes = generate_multicolumn_pdf()
    text = extract_text_from_pdf(pdf_bytes)

    assert "Data Structures" in text
    assert "Cloud Computing" in text


def test_extract_text_from_empty_pdf_raises_error() -> None:
    pdf_bytes = generate_empty_pdf()
    with pytest.raises(EmptyPDFError, match="does not contain any extractable text"):
        extract_text_from_pdf(pdf_bytes)


def test_empty_bytes_raises_error() -> None:
    with pytest.raises(EmptyPDFError, match="PDF source is empty"):
        extract_text_from_pdf(b"")


def test_page_limit_enforced() -> None:
    pdf_bytes = generate_multipage_pdf(5)
    with pytest.raises(PDFPageLimitExceededError, match="exceeds limit of 3 pages"):
        extract_text_from_pdf(pdf_bytes, max_pages=3)


def test_size_limit_enforced() -> None:
    pdf_bytes = generate_simple_text_pdf()
    with pytest.raises(PDFSizeLimitExceededError, match="exceeds limit of 100 bytes"):
        extract_text_from_pdf(pdf_bytes, max_size=100)


def test_corrupt_pdf_raises_parsing_error() -> None:
    corrupt_bytes = b"%PDF-1.4\ncorrupted content that cannot be parsed by any pdf tool"
    with pytest.raises(PDFParsingError):
        extract_text_from_pdf(corrupt_bytes)


def test_fallback_to_pypdf_when_pdfplumber_fails() -> None:
    pdf_bytes = generate_simple_text_pdf()

    with patch(
        "pdfplumber.open", side_effect=RuntimeError("Simulated pdfplumber error")
    ):
        text = extract_text_from_pdf(pdf_bytes)
        assert "Machine Learning and Deep Systems" in text
