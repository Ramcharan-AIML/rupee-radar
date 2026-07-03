"""[9] LLM Provider Factory.

Returns the correct active LLMProvider client based on application configuration.
"""

from __future__ import annotations

from app.config import get_settings
from app.llm.groq_provider import GroqProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.provider import LLMProvider


def get_llm_provider() -> LLMProvider | None:
    """Instantiate and return the configured active LLM provider.

    Returns None if LLM services are set to 'none' or disabled.
    """
    settings = get_settings()

    if not settings.llm_enabled:
        return None

    if settings.llm_provider == "groq":
        return GroqProvider()
    if settings.llm_provider == "ollama":
        return OllamaProvider()

    return None
