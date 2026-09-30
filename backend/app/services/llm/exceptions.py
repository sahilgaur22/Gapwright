class LLMError(Exception):
    """Base exception for all LLM provider errors."""

    pass


class RateLimitError(LLMError):
    """Raised when an LLM provider returns a 429 rate limit exceeded response."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ProviderUnavailableError(LLMError):
    """Raised when an LLM provider is down or returns 5xx/connectivity errors."""

    pass


class InvalidAPIKeyError(LLMError):
    """Raised when authentication fails due to a missing or invalid API key."""

    pass


class ModelResponseError(LLMError):
    """Raised when the LLM returns invalid JSON or malformed output."""

    pass
