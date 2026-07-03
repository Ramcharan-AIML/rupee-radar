import os
import pytest

from app.config import get_settings
from app.llm.cache import get_cached_category, set_cached_category
from app.store.db import init_db


@pytest.fixture(autouse=True)
def test_db():
    settings = get_settings()
    original_path = settings.db_path
    temp_path = "./data/test_cache_run.db"
    settings.db_path = temp_path

    init_db()

    yield

    settings.db_path = original_path

    for path in (temp_path, temp_path + "-wal", temp_path + "-shm"):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def test_category_cache_hits_and_misses():
    # Cache miss
    assert get_cached_category("SWIGGY") is None

    # Set cache
    set_cached_category("SWIGGY", "Food", 0.95)

    # Cache hit
    cached = get_cached_category("SWIGGY")
    assert cached is not None
    assert cached[0] == "Food"
    assert cached[1] == 0.95

    # Overwrite cache
    set_cached_category("SWIGGY", "Shopping", 0.8)
    cached = get_cached_category("SWIGGY")
    assert cached is not None
    assert cached[0] == "Shopping"
    assert cached[1] == 0.8
