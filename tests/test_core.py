"""Tests for shadowcache.core -- the ShadowCache connection wrapper."""

import json
import time
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from shadowcache.core import ShadowCache, _build_cache_key, _deserialize, _serialize
from shadowcache.exceptions import CacheBackendError


# ------------------------------------------------------------------- fixtures


@pytest.fixture
def mock_redis():
    """Return a MagicMock that mimics a redis.Redis client."""
    r = MagicMock()
    r.get.return_value = None  # cache miss by default
    r.ping.return_value = True
    return r


@pytest.fixture
def mock_db():
    """Return a MagicMock that mimics a MySQL DB-API2 connection."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [{"id": 1, "name": "Alice"}]
    type(conn).cursor = MagicMock(return_value=cursor)
    return conn


@pytest.fixture
def cache(mock_db, mock_redis):
    """A ShadowCache instance backed by mock objects."""
    return ShadowCache(mock_db, redis_client=mock_redis)


# --------------------------------------------------------------- unit helpers


class TestBuildCacheKey:
    def test_same_sql_same_key(self):
        assert _build_cache_key("shadowcache", "SELECT 1", None) == _build_cache_key("shadowcache", "SELECT 1", None)

    def test_params_change_key(self):
        a = _build_cache_key("shadowcache", "SELECT * FROM t WHERE x = %s", ("a",))
        b = _build_cache_key("shadowcache", "SELECT * FROM t WHERE x = %s", ("b",))
        assert a != b

    def test_whitespace_changes_key(self):
        a = _build_cache_key("shadowcache", "SELECT 1", None)
        b = _build_cache_key("shadowcache", "  SELECT 1", None)
        assert a != b


class TestSerializeRoundtrip:
    def test_list_of_dicts(self):
        rows = [{"a": 1, "b": "hello"}]
        payload = _serialize(rows)
        restored = _deserialize(payload)
        assert restored == rows

    def test_empty_list(self):
        rows = []
        payload = _serialize(rows)
        restored = _deserialize(payload)
        assert restored == []

    def test_none_value(self):
        rows = [{"a": None}]
        payload = _serialize(rows)
        restored = _deserialize(payload)
        assert restored == rows


# ------------------------------------------------------------------- cache ops


class TestCacheHitMiss:
    def test_cache_hit_returns_cached_rows(self, mock_db, mock_redis):
        cached = [{"id": 2, "name": "Bob"}]
        mock_redis.get.return_value = _serialize(cached)

        sc = ShadowCache(mock_db, redis_client=mock_redis)
        cursor, rows = sc.execute("SELECT * FROM users WHERE id = %s", (2,))

        assert cursor is None
        assert rows == cached
        assert sc.stats["hits"] == 1
        assert sc.stats["misses"] == 0

    def test_cache_hit_does_not_query_mysql(self, mock_db, mock_redis):
        cached = [{"id": 2}]
        mock_redis.get.return_value = _serialize(cached)

        sc = ShadowCache(mock_db, redis_client=mock_redis)
        sc.execute("SELECT * FROM users WHERE id = %s", (2,))

        mock_db.cursor.assert_not_called()

    def test_cache_miss_queries_mysql(self, mock_db, mock_redis):
        mock_redis.get.return_value = None

        sc = ShadowCache(mock_db, redis_client=mock_redis)
        cursor, rows = sc.execute("SELECT * FROM users WHERE id = %s", (1,))

        assert rows == [{"id": 1, "name": "Alice"}]
        assert sc.stats["misses"] == 1
        assert sc.stats["hits"] == 0


class TestAutoInvalidation:
    def test_insert_evicts_table_cache(self, mock_db, mock_redis):
        sc = ShadowCache(mock_db, redis_client=mock_redis)

        # Prime the cache with a SELECT on 'users'.
        mock_redis.get.return_value = None  # miss
        sc.execute("SELECT * FROM users WHERE id = %s", (1,))

        # The result should have been stored.
        assert mock_redis.set.called

        # Now perform an INSERT.
        sc.execute("INSERT INTO users (name) VALUES (%s)", ("Charlie",))

        # It should have cleared the 'users' index.
        mock_redis.smembers.assert_called()
        mock_redis.delete.assert_called()

    def test_update_evicts_table_cache(self, mock_db, mock_redis):
        sc = ShadowCache(mock_db, redis_client=mock_redis)
        sc.execute("UPDATE users SET name = %s WHERE id = %s", ("Alice", 1))
        # The write should trigger invalidation for 'users'.
        mock_redis.smembers.assert_called()

    def test_delete_evicts_table_cache(self, mock_db, mock_redis):
        sc = ShadowCache(mock_db, redis_client=mock_redis)
        sc.execute("DELETE FROM users WHERE id = %s", (1,))
        mock_redis.smembers.assert_called()

    def test_auto_invalidate_disabled(self, mock_db, mock_redis):
        sc = ShadowCache(mock_db, redis_client=mock_redis, auto_invalidate=False)
        mock_redis.reset_mock()

        sc.execute("UPDATE users SET name = %s WHERE id = %s", ("Alice", 1))
        # smembers should NOT have been called.
        mock_redis.smembers.assert_not_called()


class TestInvalidateTable:
    def test_removes_index_and_keys(self, mock_db, mock_redis):
        mock_redis.smembers.return_value = {"key1", "key2"}
        mock_redis.delete.return_value = 3

        sc = ShadowCache(mock_db, redis_client=mock_redis)
        removed = sc.invalidate_table("users")

        assert removed == 3
        mock_redis.delete.assert_called()


class TestFlushCache:
    def test_scan_and_delete(self, mock_db, mock_redis):
        mock_redis.scan_iter.return_value = iter(["k1", "k2", "k3"])
        mock_redis.delete.return_value = 3

        sc = ShadowCache(mock_db, redis_client=mock_redis)
        removed = sc.flush_cache()

        assert removed == 3


class TestStats:
    def test_initial_zero(self, mock_db, mock_redis):
        sc = ShadowCache(mock_db, redis_client=mock_redis)
        s = sc.stats
        assert s["hits"] == 0
        assert s["misses"] == 0
        assert s["hit_ratio"] == 0.0

    def test_hit_ratio(self, mock_db, mock_redis):
        sc = ShadowCache(mock_db, redis_client=mock_redis)
        sc._hits = 7
        sc._misses = 3
        assert sc.stats["hit_ratio"] == 0.7


class TestClose:
    def test_closes_db_connection(self, mock_db, mock_redis):
        sc = ShadowCache(mock_db, redis_client=mock_redis)
        sc.close()
        mock_db.close.assert_called_once()


class TestConstructor:
    def test_raises_when_redis_unreachable(self, mock_db):
        with patch("shadowcache.core.redis.Redis") as MockRedis:
            instance = MockRedis.return_value
            instance.ping.side_effect = Exception("connection refused")
            with pytest.raises(CacheBackendError):
                ShadowCache(mock_db)


class TestPassThrough:
    """Statements that are neither SELECT nor write should pass through."""

    def test_create_table(self, mock_db, mock_redis):
        sc = ShadowCache(mock_db, redis_client=mock_redis)
        sc.execute("CREATE TABLE t (id INT)")
        # Should have executed against MySQL.
        mock_db.cursor.assert_called()

    def test_set_variable(self, mock_db, mock_redis):
        sc = ShadowCache(mock_db, redis_client=mock_redis)
        sc.execute("SET @x = 1")
        mock_db.cursor.assert_called()


class TestRedisFallback:
    """When Redis is down, queries should still hit MySQL."""

    def test_select_falls_through_on_redis_error(self, mock_db, mock_redis):
        mock_redis.get.side_effect = Exception("redis gone")

        sc = ShadowCache(mock_db, redis_client=mock_redis)
        cursor, rows = sc.execute("SELECT * FROM users WHERE id = %s", (1,))

        assert rows == [{"id": 1, "name": "Alice"}]
