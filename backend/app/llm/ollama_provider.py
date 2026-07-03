"""[9] Ollama LLM Provider.

Calls local Ollama chat endpoints via HTTPX.
Enforces JSON formats and tracks local token counts.
"""

from __future__ import annotations

import json
import logging
import httpx

from app.config import get_settings
from app.llm.budget import would_exceed, record_usage
from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Client for Ollama local LLM completions using HTTPX REST calls."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_url = "http://localhost:11434/api/chat"

    def _call_api(self, messages: list[dict[str, str]], response_json: bool = False) -> str:
        """Helper to invoke Ollama local API with soft daily budget checks."""
        # Pre-flight budget guard (mainly checks soft cap for Ollama)
        projected = self.settings.llm_max_tokens_per_call
        blocked, reason = would_exceed(projected)
        if blocked:
            raise RuntimeError(f"Request blocked by LLM budget: {reason}")

        payload: dict[str, any] = {
            "model": self.settings.ollama_model,
            "messages": messages,
            "stream": False,
        }
        if response_json:
            payload["format"] = "json"

        try:
            response = httpx.post(self.api_url, json=payload, timeout=30.0)
            response.raise_for_status()
        except httpx.HTTPError as err:
            logger.error("Ollama HTTP call failed: %s", err)
            raise RuntimeError(f"Ollama local API connection error: {err}") from err

        data = response.json()
        content = data["message"]["content"]

        # Parse evaluation counts as local token usage stats
        prompt = data.get("prompt_eval_count", 0)
        completion = data.get("eval_count", 0)
        record_usage(prompt, completion)

        return content

    def classify_batch(self, descriptions: list[str]) -> dict[str, tuple[str, float]]:
        """Batch classify merchant descriptions into canonical categories."""
        if not descriptions:
            return {}

        system_prompt = (
            "You are a finance assistant. Classify the list of transaction descriptions into "
            "one of the following 10 canonical categories:\n"
            "- Food\n- Travel\n- Shopping\n- Bills\n- EMI\n- Subscriptions\n- Salary\n- Rent\n"
            "- Investments\n- Other\n\n"
            "You MUST respond with a single JSON object containing a list of classification objects "
            "exactly matching this schema:\n"
            "{\n"
            '  "classifications": [\n'
            '    {"merchant": "original description string", "category": "category name", "confidence": 0.0}\n'
            "  ]\n"
            "}\n"
            "Ensure the category matches exactly. Confidences should represent your classification probability."
        )

        user_prompt = f"Classify these merchant strings: {json.dumps(descriptions)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw_content = self._call_api(messages, response_json=True)

        try:
            parsed = json.loads(raw_content)
            classifications = parsed.get("classifications", [])
            results = {}
            for item in classifications:
                merchant = item.get("merchant")
                category = item.get("category", "Other")
                confidence = item.get("confidence", 0.0)
                if merchant:
                    results[merchant] = (category, confidence)
            return results
        except (json.JSONDecodeError, KeyError, TypeError) as err:
            logger.error("Failed to parse Ollama classification output: %s. Raw: %s", err, raw_content)
            raise RuntimeError(f"Failed to parse classification output: {err}") from err

    def complete(self, prompt: str, system_prompt: str = "") -> str:
        """Standard prompt completion."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._call_api(messages)

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Ground chat completion."""
        return self._call_api(messages)
