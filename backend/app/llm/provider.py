"""[9] LLM Provider Protocol.

Defines the structure for LLM clients used in categorization, insights, and chat.
"""

from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Abstract interface representing a text completion / categorization LLM client."""

    def classify_batch(self, descriptions: list[str]) -> dict[str, tuple[str, float]]:
        """Classify a batch of merchant descriptions into canonical categories.

        Returns a dictionary mapping description -> (category, confidence).
        """
        ...

    def complete(self, prompt: str, system_prompt: str = "") -> str:
        """Execute a simple prompt completion request."""
        ...

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Perform a multi-turn chat interaction with the model."""
        ...
