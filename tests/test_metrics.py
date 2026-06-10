"""Tests for shadowcache.metrics."""

import pytest


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics globals before each test so tests are isolated."""
    import shadowcache.metrics as m

    m.CACHE_HITS = None
    m.CACHE_MISSES = None
    m.DB_QUERY_TIME = None
    m._server_started = False


class TestLazyInit:
    def test_globals_are_none_on_import(self):
        import shadowcache.metrics as m

        assert m.CACHE_HITS is None
        assert m.CACHE_MISSES is None
        assert m.DB_QUERY_TIME is None

    def test_init_metrics_populates_globals(self):
        import shadowcache.metrics as m

        m._init_metrics()
        assert m.CACHE_HITS is not None
        assert m.CACHE_MISSES is not None
        assert m.DB_QUERY_TIME is not None

    def test_init_metrics_is_idempotent(self):
        import shadowcache.metrics as m

        m._init_metrics()
        first = id(m.CACHE_HITS)
        m._init_metrics()
        second = id(m.CACHE_HITS)
        assert first == second


class TestRecordHitMiss:
    def test_record_hit_before_init_is_noop(self):
        import shadowcache.metrics as m

        # Should not raise.
        m.record_hit()

    def test_record_hit_after_init(self):
        import shadowcache.metrics as m

        m._init_metrics()
        before = m.CACHE_HITS._value.get()
        m.record_hit()
        assert m.CACHE_HITS._value.get() == before + 1

    def test_record_miss_after_init(self):
        import shadowcache.metrics as m

        m._init_metrics()
        before = m.CACHE_MISSES._value.get()
        m.record_miss()
        assert m.CACHE_MISSES._value.get() == before + 1


class TestTrackDbTime:
    def test_returns_context_manager_when_initialised(self):
        import shadowcache.metrics as m

        m._init_metrics()
        ctx = m.track_db_time()
        assert hasattr(ctx, "__enter__")
        assert hasattr(ctx, "__exit__")

    def test_returns_noop_when_not_initialised(self):
        import shadowcache.metrics as m

        ctx = m.track_db_time()
        assert hasattr(ctx, "__enter__")
        assert hasattr(ctx, "__exit__")

    def test_context_manager_works(self):
        import shadowcache.metrics as m

        m._init_metrics()
        before = m.DB_QUERY_TIME._sum.get()
        with m.track_db_time():
            pass
        after = m.DB_QUERY_TIME._sum.get()
        assert after > before
