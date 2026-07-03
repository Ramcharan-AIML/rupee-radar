"""Ensure configuration always stays inside the Groq free-tier rate limits."""

from __future__ import annotations

from app.config import Settings
from app.llm.limits import limits_for


def test_known_groq_limits():
    limits = limits_for("groq", "llama-3.3-70b-versatile")
    assert limits is not None
    assert limits.requests_per_minute == 30
    assert limits.tokens_per_minute == 1_000
    assert limits.requests_per_day == 12_000
    assert limits.tokens_per_day == 100_000


def test_other_providers_are_unlimited():
    assert limits_for("ollama", "llama3.3") is None
    assert limits_for("none", "") is None


def test_defaults_are_within_limits():
    s = Settings(_env_file=None)  # ignore any local .env
    limits = s.provider_limits
    assert limits is not None
    assert s.llm_daily_token_budget <= limits.tokens_per_day
    assert s.llm_max_tokens_per_call < limits.tokens_per_minute


def test_oversized_settings_are_clamped_to_limits():
    # Try to configure values that would, alone, breach the free-tier ceilings.
    s = Settings(
        _env_file=None,
        llm_provider="groq",
        llm_daily_token_budget=500_000,   # > TPD (100k)
        llm_max_tokens_per_call=5_000,    # > TPM (1k)
    )
    assert s.llm_daily_token_budget == 100_000          # clamped to TPD
    assert s.llm_max_tokens_per_call <= int(1_000 * 0.8)  # clamped below TPM with headroom


def test_ollama_is_not_clamped():
    s = Settings(_env_file=None, llm_provider="ollama", llm_daily_token_budget=500_000)
    assert s.llm_daily_token_budget == 500_000  # no provider ceilings for local models
