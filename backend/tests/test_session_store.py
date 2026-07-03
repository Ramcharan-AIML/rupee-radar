"""Phase 1 acceptance: session store returns Analysis before TTL, None after expiry/purge."""

from __future__ import annotations

from app.models.schemas import Analysis
from app.store.session_store import SessionStore


class FakeClock:
    """A controllable monotonic clock for deterministic TTL tests."""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def test_put_then_get_returns_same_analysis():
    store = SessionStore(ttl_minutes=60)
    analysis = Analysis()
    sid = store.put(analysis)
    assert sid == analysis.session_id
    assert store.get(sid) is analysis


def test_get_unknown_id_returns_none():
    store = SessionStore(ttl_minutes=60)
    assert store.get("does-not-exist") is None


def test_entry_available_before_ttl_and_gone_after():
    clock = FakeClock()
    store = SessionStore(ttl_minutes=10, time_fn=clock)
    sid = store.put(Analysis())

    clock.advance(9 * 60)  # still within the 10-minute TTL
    assert store.get(sid) is not None

    clock.advance(2 * 60)  # now past the TTL
    assert store.get(sid) is None


def test_purge_removes_only_expired_entries():
    clock = FakeClock()
    store = SessionStore(ttl_minutes=10, time_fn=clock)

    old_id = store.put(Analysis())
    clock.advance(11 * 60)  # old entry now expired
    fresh_id = store.put(Analysis())

    removed = store.purge()
    assert removed == 1
    assert store.get(old_id) is None
    assert store.get(fresh_id) is not None
    assert len(store) == 1


def test_get_expired_purges_lazily():
    clock = FakeClock()
    store = SessionStore(ttl_minutes=5, time_fn=clock)
    sid = store.put(Analysis())
    clock.advance(6 * 60)
    assert store.get(sid) is None  # access triggers removal
    assert len(store) == 0
