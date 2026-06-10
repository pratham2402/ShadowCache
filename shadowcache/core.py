"""Core ShadowCache class -- transparent Redis caching for raw SQL connections."""

import datetime
import hashlib
import json
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import redis

from shadowcache.exceptions import CacheBackendError
from shadowcache.logger import get_logger
from shadowcache.parser import extract_tables, extract_write_type, is_select_query

_log = get_logger(__name__)

_DEFAULT_KEY_PREFIX = "shadowcache"

# Sentinel keys for type-tagged JSON serialization.
# Each non-native value is encoded as a 3-element list:
#   ["__sc__", "<type_name>", "<payload>"]
# A list is used because it is far less likely to appear as a real column
# value than a dict with particular keys.
_SC_SENTINEL = "__sc__"


def _param_repr(value: Any) -> str:
    """Produce a type-aware string representation of a parameter value.

    Prefixes the value with its Python type name so that ``1`` (int) and
    ``"1"`` (str) produce different cache keys.
    """
    return f"{type(value).__name__}:{value}"


def _build_cache_key(prefix: str, sql: str, params: Optional[tuple]) -> str:
    """Produce a deterministic cache key from a SQL string and its parameters."""
    raw = sql
    if params:
        raw += "|" + "|".join(_param_repr(p) for p in params)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _serialize(rows: List[Dict[str, Any]]) -> str:
    """JSON-serialise rows, handling non-native types via sentinel lists.

    Supported types: bytes, datetime, date, time, timedelta, Decimal.
    Each is encoded as ``["__sc__", "<type>", "<payload>"]``.
    """

    def _default(obj: Any) -> Any:
        if isinstance(obj, bytes):
            return [_SC_SENTINEL, "bytes", obj.hex()]
        if isinstance(obj, datetime.datetime):
            return [_SC_SENTINEL, "datetime", obj.isoformat()]
        if isinstance(obj, datetime.date):
            return [_SC_SENTINEL, "date", obj.isoformat()]
        if isinstance(obj, datetime.time):
            return [_SC_SENTINEL, "time", obj.isoformat()]
        if isinstance(obj, datetime.timedelta):
            return [_SC_SENTINEL, "timedelta", obj.total_seconds()]
        if isinstance(obj, Decimal):
            return [_SC_SENTINEL, "Decimal", str(obj)]
        raise TypeError(f"Unsupported type: {type(obj)}")

    return json.dumps(rows, default=_default)


def _deserialize(payload: str) -> List[Dict[str, Any]]:
    """Deserialise rows, restoring non-native types from sentinel lists.

    Recursively walks the decoded JSON tree.  Any three-element list whose
    first element is ``_SC_SENTINEL`` is converted back to its native type;
    all other values pass through unchanged.
    """

    def _walk(obj: Any) -> Any:
        if isinstance(obj, list):
            if len(obj) == 3 and obj and obj[0] == _SC_SENTINEL:
                _, t, d = obj
                if t == "bytes":
                    return bytes.fromhex(d)
                if t == "datetime":
                    return datetime.datetime.fromisoformat(d)
                if t == "date":
                    return datetime.date.fromisoformat(d)
                if t == "time":
                    return datetime.time.fromisoformat(d)
                if t == "timedelta":
                    return datetime.timedelta(seconds=d)
                if t == "Decimal":
                    return Decimal(d)
            return [_walk(item) for item in obj]
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items()}
        return obj

    return _walk(json.loads(payload))


class ShadowCache:
    """Transparent Redis cache layer for a DB-API2 MySQL connection.

    Parameters
    ----------
    db_connection:
        An open DB-API2 connection (e.g. from ``mysql.connector.connect``).
    redis_client:
        An optional pre-configured ``redis.Redis`` instance.  If omitted a
        client bound to ``redis_host``/``redis_port`` is created.
    redis_host:
        Hostname for Redis (ignored when *redis_client* is supplied).
    redis_port:
        Port for Redis (ignored when *redis_client* is supplied).
    ttl:
        Time-to-live in seconds for cached SELECT results.  Default 300.
    auto_invalidate:
        When ``True`` (the default), INSERT/UPDATE/DELETE statements
        automatically evict cached SELECT results that reference the same
        table.
    key_prefix:
        Namespace prefix for all Redis keys.  Change this to share a Redis
        instance across multiple applications.
    """

    def __init__(
        self,
        db_connection,
        redis_client: Optional[redis.Redis] = None,
        *,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        ttl: int = 300,
        auto_invalidate: bool = True,
        key_prefix: str = _DEFAULT_KEY_PREFIX,
    ):
        self._db = db_connection
        self._ttl = ttl
        self._auto_invalidate = auto_invalidate
        self._key_prefix = key_prefix
        self._index_prefix = f"{key_prefix}:index"

        self._hits = 0
        self._misses = 0

        if redis_client is not None:
            self._redis = redis_client
        else:
            try:
                self._redis = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                )
                self._redis.ping()
            except Exception as exc:
                raise CacheBackendError(
                    f"Could not connect to Redis at {redis_host}:{redis_port}"
                ) from exc

    # ---------------------------------------------------------------- public API

    def execute(
        self,
        sql: str,
        params: Optional[tuple] = None,
    ) -> Tuple[Any, Optional[List[Dict[str, Any]]]]:
        """Execute *sql* with optional *params*, applying caching automatically.

        Returns ``(cursor, rows)``.

        *For SELECT statements* the cache is consulted first.  On a hit
        ``cursor`` is ``None`` and *rows* contains the cached result.  On a
        miss the query runs against MySQL, the result is stored in Redis,
        and both the live cursor and rows are returned.

        *For INSERT/UPDATE/DELETE* the statement runs against MySQL and any
        cached SELECT results that reference the affected tables are
        evicted.  ``rows`` is ``None``; the caller inspects ``cursor`` for
        ``.lastrowid`` or ``.rowcount``.

        *For all other statements* (DDL, administrative commands) the
        statement is forwarded to MySQL unchanged.
        """
        if not sql or not sql.strip():
            return None, None

        sql = sql.strip()

        if is_select_query(sql):
            return self._handle_select(sql, params)

        write_type = extract_write_type(sql)
        if write_type is not None:
            return self._handle_write(sql, params, write_type)

        return self._handle_other(sql, params)

    def invalidate_table(self, table_name: str) -> int:
        """Evict all cached entries associated with *table_name*.

        Returns the number of keys removed.
        """
        index_key = f"{self._index_prefix}:{table_name}"
        try:
            members = self._redis.smembers(index_key)
            if not members:
                return 0
            keys = list(members)
            keys.append(index_key)
            return self._redis.delete(*keys)
        except redis.RedisError as exc:
            _log.warning("Failed to invalidate table %r: %s", table_name, exc)
            return 0

    def flush_cache(self) -> int:
        """Remove all ShadowCache keys from Redis.

        Returns the number of keys removed.
        """
        pattern = f"{self._key_prefix}:*"
        try:
            keys = list(self._redis.scan_iter(match=pattern, count=100))
            if not keys:
                return 0
            return self._redis.delete(*keys)
        except redis.RedisError as exc:
            _log.warning("Failed to flush cache: %s", exc)
            return 0

    def close(self) -> None:
        """Close the wrapped database connection."""
        try:
            if hasattr(self._db, "close"):
                self._db.close()
        except Exception as exc:
            _log.warning("Error closing database connection: %s", exc)

    @property
    def stats(self) -> Dict[str, Any]:
        """Return a snapshot of cache performance counters."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_ratio": self._hits / total if total else 0.0,
        }

    # --------------------------------------------------------------- internals

    def _handle_select(self, sql: str, params):
        cache_key = _build_cache_key(self._key_prefix, sql, params)

        # Try Redis first.
        try:
            cached = self._redis.get(cache_key)
        except Exception as exc:
            _log.warning("Redis read error, falling through to MySQL: %s", exc)
            cached = None

        if cached is not None:
            try:
                rows = _deserialize(cached)
            except Exception as exc:
                _log.warning(
                    "Cache deserialisation failed for key %r, falling through to MySQL: %s",
                    cache_key,
                    exc,
                )
            else:
                self._hits += 1
                _log.info("Cache HIT for key %s", cache_key)
                return None, rows

        self._misses += 1
        _log.info("Cache MISS for key %s -- fetching from MySQL", cache_key)

        cursor, rows = self._handle_other(sql, params)
        if rows is None:
            return cursor, None

        # Store in Redis and update per-table indexes.
        tables = extract_tables(sql)
        self._store_result(cache_key, rows, tables)
        return cursor, rows

    def _handle_write(self, sql: str, params, write_type: str):
        cursor, _ = self._handle_other(sql, params)

        if self._auto_invalidate:
            tables = extract_tables(sql)
            for table in tables:
                self.invalidate_table(table)
            _log.debug("%s executed, tables evicted: %s", write_type, tables)

        return cursor, None

    def _handle_other(self, sql: str, params):
        """Execute SQL directly against MySQL, returning (cursor, rows).

        Rows are normalised to ``list[dict]`` regardless of whether the
        underlying driver returns tuples or dicts.  The conversion uses
        ``cursor.description`` (standard DB-API2) so the wrapper works
        with ``mysql-connector-python``, ``pymysql``, and other PEP 249
        drivers.
        """
        try:
            cursor = self._db.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
        except Exception:
            try:
                cursor.close()
            except Exception:
                pass
            raise

        try:
            raw_rows = cursor.fetchall()
        except Exception:
            raw_rows = None

        if raw_rows and cursor.description:
            first_row = raw_rows[0]
            if isinstance(first_row, dict):
                rows = raw_rows
            else:
                columns = [col[0] for col in cursor.description]
                rows = [dict(zip(columns, row)) for row in raw_rows]
        elif raw_rows is not None:
            rows = []  # empty result set
        else:
            rows = None  # fetchall failed on a non-result-set statement

        return cursor, rows

    def _store_result(self, cache_key: str, rows, tables: set):
        try:
            payload = _serialize(rows)
        except Exception as exc:
            _log.warning("Failed to serialise result for key %r: %s", cache_key, exc)
            return

        try:
            self._redis.set(cache_key, payload, ex=self._ttl)
        except redis.RedisError as exc:
            _log.warning("Failed to store cache key %r: %s", cache_key, exc)
            return

        for table in tables:
            index_key = f"{self._index_prefix}:{table}"
            try:
                self._redis.sadd(index_key, cache_key)
                self._redis.expire(index_key, self._ttl)
            except redis.RedisError as exc:
                _log.debug("Failed to update index for table %r: %s", table, exc)
