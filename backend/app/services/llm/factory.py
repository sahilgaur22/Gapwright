from app.core.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.gemini import GeminiProvider
from app.services.llm.groq import GroqProvider


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """Return an instantiated LLMProvider based on provider_name or environment.

    Supported values: 'gemini', 'groq'.
    """
    selected = (provider_name or settings.LLM_PROVIDER).strip().lower()

    if selected == "gemini":
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.LLM_MODEL,
            embed_model=settings.EMBED_MODEL,
        )
    elif selected == "groq":
        # If Gemini is configured, allow Groq to use Gemini for vector embeddings
        gemini_embed = (
            GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                embed_model=settings.EMBED_MODEL,
            )
            if settings.GEMINI_API_KEY
            else None
        )
        return GroqProvider(
            api_key=settings.GROQ_API_KEY,
            model=settings.LLM_MODEL,
            embed_model=settings.EMBED_MODEL,
            embed_provider=gemini_embed,
        )
    else:
        supported = "'gemini', 'groq'"
        raise ValueError(
            f"Unsupported LLM provider: '{selected}'. Supported: {supported}."
        )
