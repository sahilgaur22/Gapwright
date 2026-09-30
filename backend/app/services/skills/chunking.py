import re
from typing import ClassVar

from app.services.llm.budget import TokenBudgetHelper

# Patterns identifying academic syllabus section boundaries
SECTION_HEADING_PATTERNS = [
    # Markdown headers (# Heading, ## Subheading)
    re.compile(r"(?m)^(#{1,4}\s+[^\n]+)$"),
    # Academic module / week / unit markers
    re.compile(
        r"(?m)^((?:Module|Unit|Week|Lecture|Part|Chapter|Lab)\s+"
        r"\d+[:\s\-\.][^\n]+)$",
        re.IGNORECASE,
    ),
    # Standard syllabus sections (all-caps or title case)
    re.compile(
        r"(?m)^((?:COURSE DESCRIPTION|PREREQUISITES|LEARNING OUTCOMES|"
        r"COURSE OBJECTIVES|REQUIRED TEXTBOOKS|GRADING POLICY|"
        r"ASSESSMENT BREAKDOWN|ACADEMIC INTEGRITY|SCHEDULE|TENTATIVE SCHEDULE|"
        r"COURSE OUTLINE|LABORATORY TOPICS)[\s:]*)$",
        re.IGNORECASE,
    ),
    # Numbered sections like "1. Introduction", "2.1 System Architecture"
    re.compile(r"(?m)^(\d{1,2}(?:\.\d{1,2})*\s+[A-Z][^\n]{3,60})$"),
]


class SectionChunker:
    """Splits syllabus documents into section-aware chunks with token budget

    enforcement and context overlap.
    """

    DEFAULT_MAX_CHUNK_TOKENS: ClassVar[int] = 1500
    DEFAULT_OVERLAP_TOKENS: ClassVar[int] = 150

    @classmethod
    def identify_section_headings(cls, text: str) -> list[tuple[int, str]]:
        """Identify start positions and titles of section headings in text."""
        headings: list[tuple[int, str]] = []
        for pattern in SECTION_HEADING_PATTERNS:
            for match in pattern.finditer(text):
                pos = match.start()
                title = match.group(1).strip()
                headings.append((pos, title))

        headings.sort(key=lambda x: x[0])

        deduped_headings: list[tuple[int, str]] = []
        last_pos = -1
        for pos, title in headings:
            if last_pos == -1 or pos > last_pos + 10:
                deduped_headings.append((pos, title))
                last_pos = pos

        return deduped_headings

    @classmethod
    def split_into_sections(cls, text: str) -> list[tuple[str, str]]:
        """Split document into a sequence of (heading, content) tuples."""
        cleaned = text.strip()
        if not cleaned:
            return []

        headings = cls.identify_section_headings(cleaned)
        if not headings:
            return [("Overview", cleaned)]

        sections: list[tuple[str, str]] = []

        if headings[0][0] > 0:
            preamble = cleaned[: headings[0][0]].strip()
            if preamble:
                sections.append(("Introduction", preamble))

        for i, (pos, title) in enumerate(headings):
            start = pos + len(title)
            end = headings[i + 1][0] if i + 1 < len(headings) else len(cleaned)
            content = cleaned[start:end].strip()
            sections.append((title, content))

        return sections

    @classmethod
    def chunk_document(
        cls,
        text: str,
        *,
        max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
        overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    ) -> list[str]:
        """Produce section-aware chunks that each fit within max_chunk_tokens,

        preserving heading context and overlapping tokens across chunk boundaries.
        """
        cleaned = text.strip()
        if not cleaned:
            return []

        if TokenBudgetHelper.fits_budget(cleaned, max_chunk_tokens):
            return [cleaned]

        sections = cls.split_into_sections(cleaned)
        chunks: list[str] = []
        current_chunk_parts: list[str] = []
        current_tokens = 0

        for title, content in sections:
            header_prefix = "### " if not title.startswith("#") else ""
            section_header = f"{header_prefix}{title}\n"
            full_section_text = (
                f"{section_header}{content}" if content else section_header.strip()
            )
            sec_tokens = TokenBudgetHelper.estimate_tokens(full_section_text)

            # If an individual section exceeds budget, split its content
            if sec_tokens > max_chunk_tokens:
                if current_chunk_parts:
                    chunks.append("\n\n".join(current_chunk_parts))
                    current_chunk_parts = []
                    current_tokens = 0

                content_budget = max_chunk_tokens - TokenBudgetHelper.estimate_tokens(
                    section_header
                )
                sub_chunks = TokenBudgetHelper.chunk_text(
                    content,
                    max_tokens=max(200, content_budget),
                    overlap_tokens=overlap_tokens,
                )
                for sub in sub_chunks:
                    chunks.append(f"{section_header}{sub}")
                continue

            # If adding this section exceeds budget, flush current chunk
            if current_tokens + sec_tokens > max_chunk_tokens and current_chunk_parts:
                chunks.append("\n\n".join(current_chunk_parts))

                overlap_budget = 0
                new_parts: list[str] = []
                for prev_part in reversed(current_chunk_parts):
                    t = TokenBudgetHelper.estimate_tokens(prev_part)
                    if overlap_budget + t <= overlap_tokens:
                        new_parts.insert(0, prev_part)
                        overlap_budget += t
                    else:
                        break

                current_chunk_parts = new_parts
                current_tokens = overlap_budget

            current_chunk_parts.append(full_section_text)
            current_tokens += sec_tokens

        if current_chunk_parts:
            chunks.append("\n\n".join(current_chunk_parts))

        return chunks
