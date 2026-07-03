import os
import time
from datetime import datetime, timezone
import pytest

from app.config import get_settings
from app.llm.budget import get_retry_after, get_rolling_usage, record_usage, would_exceed
from app.store.db import init_db


@pytest.fixture(autouse=True)
def test_db():
    settings = get_settings()
    original_path = settings.db_path
    temp_path = "./data/test_budget_run.db"
    settings.db_path = temp_path

    init_db()

    # Configure provider for test settings
    original_provider = settings.llm_provider
    original_key = settings.groq_api_key
    original_rpm = settings.groq_rpm_limit
    original_tpm = settings.groq_tpm_limit

    settings.llm_provider = "groq"
    settings.groq_api_key = "test_key"

    yield

    settings.db_path = original_path
    settings.llm_provider = original_provider
    settings.groq_api_key = original_key
    settings.groq_rpm_limit = original_rpm
    settings.groq_tpm_limit = original_tpm

    for path in (temp_path, temp_path + "-wal", temp_path + "-shm"):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def test_record_usage_and_rolling_calculations():
    # Verify starting state
    usage = get_rolling_usage()
    assert usage["rpm"] == 0
    assert usage["tpm"] == 0
    assert usage["rpd"] == 0
    assert usage["tpd"] == 0

    # Record first call
    record_usage(prompt_tokens=100, completion_tokens=50)

    usage = get_rolling_usage()
    assert usage["rpm"] == 1
    assert usage["tpm"] == 150
    assert usage["rpd"] == 1
    assert usage["tpd"] == 150


def test_would_exceed_checks():
    settings = get_settings()
    # Mock limits to small ceilings
    settings.groq_rpm_limit = 2
    settings.groq_tpm_limit = 200

    # We shouldn't exceed limits initially
    blocked, reason = would_exceed(50)
    assert blocked is False

    # Record a large call
    record_usage(prompt_tokens=100, completion_tokens=50)  # 150 total

    # 150 + 60 = 210 > TPM 200 limit
    blocked, reason = would_exceed(60)
    assert blocked is True
    assert "TPM" in reason

    # Record another call
    record_usage(prompt_tokens=20, completion_tokens=10)  # Total calls: 2, Total tokens: 180

    # Next call breaches RPM limit (limit is 2, 3rd call will exceed)
    blocked, reason = would_exceed(10)
    assert blocked is True
    assert "RPM" in reason


def test_retry_after_calculation():
    settings = get_settings()
    settings.groq_rpm_limit = 2
    settings.groq_tpm_limit = 100

    # No wait initially
    assert get_retry_after(10) == 0.0

    # Fill TPM
    record_usage(prompt_tokens=50, completion_tokens=40)  # 90 tokens, call 1

    # Remaining 10 tokens. Request for 20 exceeds TPM
    retry_after = get_retry_after(20)
    assert retry_after > 0.0
    assert retry_after <= 60.0
