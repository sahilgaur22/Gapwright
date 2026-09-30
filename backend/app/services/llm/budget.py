import re


class TokenBudgetHelper:
    """Helper for estimating token counts, verifying budgets, and chunking text."""

    CHARS_PER_TOKEN: float = 4.0

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Estimate token count for a text string using average characters per token."""
        if not text:
            return 0
        return max(1, int(len(text) / cls.CHARS_PER_TOKEN))

    @classmethod
    def fits_budget(cls, text: str, max_tokens: int) -> bool:
        """Check if text fits within a specified token budget."""
        return cls.estimate_tokens(text) <= max_tokens

    @classmethod
    def truncate_to_budget(cls, text: str, max_tokens: int) -> str:
        """Truncate text to fit within max_tokens at the nearest word boundary."""
        if cls.fits_budget(text, max_tokens):
            return text

        max_chars = int(max_tokens * cls.CHARS_PER_TOKEN)
        truncated = text[:max_chars]
        # Trim back to last whitespace if possible to avoid breaking a word in half
        last_space = truncated.rfind(" ")
        if last_space > int(max_chars * 0.7):
            truncated = truncated[:last_space]

        return truncated.strip()

    @classmethod
    def chunk_text(
        cls,
        text: str,
        max_tokens: int,
        overlap_tokens: int = 50,
    ) -> list[str]:
        """Split text into overlapping chunks that each fit within max_tokens.

        Prefers splitting on paragraphs, then sentences, then words.
        """
        if not text.strip():
            return []

        if cls.fits_budget(text, max_tokens):
            return [text.strip()]

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = cls.estimate_tokens(para)

            # If a single paragraph exceeds max_tokens, split it by lines or sentences
            if para_tokens > max_tokens:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", para) if s]
                sub_chunk: list[str] = []
                sub_tokens = 0

                for sentence in sentences:
                    s_tokens = cls.estimate_tokens(sentence)
                    if sub_tokens + s_tokens > max_tokens and sub_chunk:
                        chunks.append(" ".join(sub_chunk))
                        # Keep overlap from the end of the previous subchunk
                        overlap_budget = 0
                        new_sub: list[str] = []
                        for prev_s in reversed(sub_chunk):
                            t = cls.estimate_tokens(prev_s)
                            if overlap_budget + t <= overlap_tokens:
                                new_sub.insert(0, prev_s)
                                overlap_budget += t
                            else:
                                break
                        sub_chunk = new_sub
                        sub_tokens = overlap_budget

                    sub_chunk.append(sentence)
                    sub_tokens += s_tokens

                if sub_chunk:
                    chunks.append(" ".join(sub_chunk))
                continue

            if current_tokens + para_tokens > max_tokens and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                # Calculate overlap paragraphs
                overlap_budget = 0
                new_chunk: list[str] = []
                for prev_p in reversed(current_chunk):
                    t = cls.estimate_tokens(prev_p)
                    if overlap_budget + t <= overlap_tokens:
                        new_chunk.insert(0, prev_p)
                        overlap_budget += t
                    else:
                        break
                current_chunk = new_chunk
                current_tokens = overlap_budget

            current_chunk.append(para)
            current_tokens += para_tokens

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks
