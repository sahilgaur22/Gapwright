class ParsingError(Exception):
    """Base exception for all document parsing errors."""

    pass


class UnsupportedFormatError(ParsingError):
    """Raised when a document format is not supported for parsing."""

    pass


class PDFParsingError(ParsingError):
    """Base exception for PDF parsing errors."""

    pass


class PDFSizeLimitExceededError(PDFParsingError):
    """Raised when PDF file size exceeds the allowed limit."""

    pass


class PDFPageLimitExceededError(PDFParsingError):
    """Raised when PDF page count exceeds the allowed limit."""

    pass


class EmptyPDFError(PDFParsingError):
    """Raised when the parsed PDF contains no extractable text."""

    pass


class DOCXParsingError(ParsingError):
    """Base exception for DOCX parsing errors."""

    pass


class DOCXSizeLimitExceededError(DOCXParsingError):
    """Raised when DOCX file size exceeds the allowed limit."""

    pass


class EmptyDOCXError(DOCXParsingError):
    """Raised when the parsed DOCX contains no extractable text."""

    pass
