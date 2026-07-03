"""[9] Groq LLM Provider.

Calls api.groq.com chat completion endpoints via HTTPX.
Enforces strict JSON formatting, low temperature, and logs token usage.
"""

from __future__ import annotations

import json
import logging
import httpx

from app.config import get_settings
from app.llm.budget import would_exceed, record_usage
from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """Client for Groq LLM completions using HTTPX REST calls."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def _call_api(self, messages: list[dict[str, str]], response_json: bool = False) -> str:
        """Helper to invoke Groq completions API with limits pre-flight checks."""
        # Pre-flight budget guard
        projected = self.settings.llm_max_tokens_per_call
        blocked, reason = would_exceed(projected)
        if blocked:
            raise RuntimeError(f"Request blocked by LLM budget: {reason}")

        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, any] = {
            "model": self.settings.groq_model,
            "messages": messages,
            "temperature": 0.0,
        }
        if response_json:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = httpx.post(self.api_url, headers=headers, json=payload, timeout=12.0)
            if response.status_code == 429:
                retry = response.headers.get("Retry-After", "1.0")
                raise RuntimeError(f"Groq API 429 Rate Limited. Retry after: {retry}s")
            response.raise_for_status()
        except httpx.HTTPError as err:
            logger.error("Groq HTTP call failed: %s", err)
            raise RuntimeError(f"Groq API connection error: {err}") from err

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # Parse usage stats and record them
        usage = data.get("usage", {})
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
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
            parsed = json.loads(_clean_json_text(raw_content))
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
            logger.error("Failed to parse Groq classification output: %s. Raw: %s", err, raw_content)
            # Raise so the caller can fallback
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


def _clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
