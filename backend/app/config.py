"""Application configuration.

Settings are read from environment variables / a local `.env` file (see `.env.example`).
This is the single source of truth for the LLM provider, token budgets, and limits referenced
throughout the architecture (§8). Phase 0 only needs the provider/health fields populated;
later phases consume the budget and storage settings.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.llm.limits import RateLimits, limits_for


class Settings(BaseSettings):
    """Typed application settings loaded from the environment / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Provider ---
    llm_provider: Literal["groq", "ollama", "none"] = "groq"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_model: str = "llama3.3"

    # --- Groq free-tier rate limits for llama-3.3-70b-versatile (the binding ceilings the
    #     Phase 8 budget guard enforces). TPM = 1,000 is the tightest constraint. Override via
    #     env only if your account's limits differ. ---
    groq_rpm_limit: int = 30          # requests / minute
    groq_tpm_limit: int = 1_000       # tokens / minute   <-- binding constraint
    groq_rpd_limit: int = 12_000      # requests / day
    groq_tpd_limit: int = 100_000     # tokens / day

    # --- Token budget / cost control (free-tier guard) ---
    # Defaults kept safely inside the limits above. The budget guard (Phase 8) also enforces
    # all four rolling windows (RPM/TPM/RPD/TPD) regardless of these soft settings.
    llm_daily_token_budget: int = 100_000   # soft daily cap; clamped to groq_tpd_limit
    llm_max_tokens_per_call: int = 500       # completion cap; clamped below groq_tpm_limit
    llm_categorize_batch: int = 15           # small enough that one call stays well under TPM
    llm_enable_chat: bool = True
    llm_enable_narrative: bool = True
    llm_insight_mode: Literal["off", "polish", "generate"] = "polish"

    # --- Storage & limits ---
    db_path: str = "./data/rupeeradar.db"
    session_ttl_minutes: int = 60  # in-memory session store TTL (until DB lands in Phase 7)
    max_upload_mb: int = 10

    # --- Server / CORS ---
    frontend_origin: str = "http://localhost:5173"

    @property
    def llm_enabled(self) -> bool:
        """Whether AI features can actually run with the current configuration.

        ``groq`` requires an API key; ``ollama`` runs locally; ``none`` disables AI.
        """
        if self.llm_provider == "none":
            return False
        if self.llm_provider == "groq":
            return bool(self.groq_api_key)
        return True  # ollama

    @property
    def active_model(self) -> str:
        """The model name for the selected provider (empty when disabled)."""
        if self.llm_provider == "groq":
            return self.groq_model
        if self.llm_provider == "ollama":
            return self.ollama_model
        return ""

    @property
    def provider_limits(self) -> RateLimits | None:
        """Rate limits for the active provider/model (None = unlimited, e.g. ollama/none)."""
        return limits_for(self.llm_provider, self.active_model)

    @model_validator(mode="after")
    def _clamp_to_provider_limits(self) -> "Settings":
        """Keep soft budgets inside the provider's hard ceilings so we never configure a
        setting that would, on its own, exceed a free-tier limit."""
        limits = limits_for(self.llm_provider, self.active_model)
        if limits is not None:
            # Daily soft budget can never exceed the provider's tokens-per-day ceiling.
            self.llm_daily_token_budget = min(self.llm_daily_token_budget, limits.tokens_per_day)
            # A single call's completion must leave room for its prompt within the TPM window;
            # cap it below TPM (reserve ~20% for the input/prompt).
            tpm_call_cap = max(1, int(limits.tokens_per_minute * 0.8))
            self.llm_max_tokens_per_call = min(self.llm_max_tokens_per_call, tpm_call_cap)
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance (one load per process)."""
    return Settings()
