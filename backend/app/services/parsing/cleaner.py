import re

# Regex for common bullet markers (unicode and ascii) at the start of a line
BULLET_PATTERN = re.compile(r"(?m)^([ \t]*)[•◦▪▫⁃‣\*\–—][ \t]+")

# Regex for words hyphenated across a line wrap
HYPHENATED_WRAP_PATTERN = re.compile(r"(\b[a-zA-Z]{2,})-\s*\n\s*([a-zA-Z]{2,}\b)")

# Regex patterns for page numbers, headers, and footers
PAGE_HEADER_FOOTER_PATTERNS = [
    re.compile(
        r"(?im)^[ \t]*(?:[-–—]+\s*)?(?:page|pg\.?)\s*[:#]?\s*\d+"
        r"(?:\s*(?:of|\/)\s*\d+)?(?:\s*[-–—]+)?[ \t]*$"
    ),
    re.compile(r"(?m)^[ \t]*[-–—]+\s*\d+\s*[-–—]+[ \t]*$"),
    re.compile(r"(?im)^[ \t]*\d+\s*(?:of|\/)\s*\d+[ \t]*$"),
    re.compile(r"(?im)^[ \t]*\[\s*page\s*\d+\s*\][ \t]*$"),
]

# Multiple horizontal whitespace (spaces, non-breaking spaces, tabs)
HORIZONTAL_WHITESPACE_PATTERN = re.compile(r"[^\S\r\n]+")

# Multiple consecutive blank lines
CONSECUTIVE_NEWLINES_PATTERN = re.compile(r"\n{3,}")


def fix_line_hyphenation(text: str) -> str:
    """Recombine words split across line breaks with a trailing hyphen."""
    return HYPHENATED_WRAP_PATTERN.sub(r"\1\2", text)


def normalize_bullets(text: str) -> str:
    """Normalize varied bullet point markers (•, ◦, ▪, etc.) to markdown '- '."""
    return BULLET_PATTERN.sub(r"\1- ", text)


def remove_headers_footers(text: str) -> str:
    """Remove common page number and header/footer artifacts from documents."""
    result = text
    for pattern in PAGE_HEADER_FOOTER_PATTERNS:
        result = pattern.sub("", result)
    return result


def normalize_whitespace(text: str) -> str:
    """Normalize line endings, horizontal spacing, and excessive blank lines."""
    # Convert carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Replace non-breaking spaces and tabs with standard space
    text = text.replace("\u00a0", " ")

    # Process line by line
    cleaned_lines = []
    for line in text.split("\n"):
        line = HORIZONTAL_WHITESPACE_PATTERN.sub(" ", line).strip()
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    # Collapse 3+ newlines into 2
    text = CONSECUTIVE_NEWLINES_PATTERN.sub("\n\n", text)
    return text.strip()


def clean_text(text: str) -> str:
    """Apply the full text cleaning pipeline for parsed syllabus documents.

    Pipeline:
        1. Initial whitespace normalization
        2. Fix hyphenated line-wraps
        3. Standardize bullet points
        4. Remove repetitive header/footer page markers
        5. Final whitespace normalization and trimming
    """
    if not text:
        return ""

    text = normalize_whitespace(text)
    text = fix_line_hyphenation(text)
    text = normalize_bullets(text)
    text = remove_headers_footers(text)
    text = normalize_whitespace(text)

    return text
