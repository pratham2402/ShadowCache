![Star Badge](https://img.shields.io/static/v1?label=%F0%9F%8C%9F&message=If%20Useful&style=style=flat&color=BC4E99)
![Open Source Love](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)
[![View My Profile](https://img.shields.io/badge/View-My_Profile-green?logo=GitHub)](https://github.com/pratham2402)
[![View Repositories](https://img.shields.io/badge/View-My_Repositories-blue?logo=GitHub)](https://github.com/pratham2402?tab=repositories)

# ShadowCache

![ShadowCache Banner](./README%20Banner%20Art.png)

ShadowCache is a Python library that adds transparent Redis caching to raw MySQL
connections. It wraps a DB-API2 connection and caches SELECT results automatically.
When you run an INSERT, UPDATE, or DELETE, it evicts the affected cache entries so
your reads never serve stale data. No ORM required.

## Features

- **Zero-schema caching**. Works with any MySQL table, any query. No model
  definitions needed.
- **Write-triggered eviction**. INSERT, UPDATE, and DELETE statements
  automatically evict cached SELECT results for the same table.
- **TTL safety net**. Cached entries expire after a configurable time-to-live,
  so eventual consistency is guaranteed even when SQL parsing fails.
- **Prometheus metrics**. Optional counters for cache hits, misses, and MySQL
  query execution time.
- **Graceful fallback**. If Redis is unreachable, queries still execute
  against MySQL.

## Installation

```bash
pip install shadowcache
```

Or install from source:

```bash
git clone https://github.com/pratham2402/ShadowCache.git
cd ShadowCache
pip install -r requirements.txt
```

### Dependencies

- Python 3.8+
- Redis (local or remote)
- MySQL database

## Quick Start

```python
import mysql.connector
from shadowcache import ShadowCache

conn = mysql.connector.connect(
    host="localhost",
    database="my_app",
    user="app_user",
    password="secret",
)

cache = ShadowCache(conn)

# First call hits MySQL, result is cached in Redis.
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))
for row in rows:
    print(row["name"])

# Second call with same SQL + params returns from cache instantly.
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))

# A write evicts cached SELECTs that reference the 'users' table.
cache.execute("UPDATE users SET name = %s WHERE id = %s", ("Alice", 42))

# Next SELECT goes to MySQL again (cache was evicted). Fresh data.
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))
```

## API

### `ShadowCache(db_connection, *, redis_client=None, redis_host="localhost", redis_port=6379, ttl=300, auto_invalidate=True)`

Wraps a DB-API2 connection. All parameters except `db_connection` are keyword-only.

| Parameter | Default | Description |
|---|---|---|
| `db_connection` | (required) | An open DB-API2 MySQL connection |
| `redis_client` | `None` | Pre-configured `redis.Redis` instance; created automatically if omitted |
| `redis_host` | `"localhost"` | Redis hostname (ignored if `redis_client` is provided) |
| `redis_port` | `6379` | Redis port (ignored if `redis_client` is provided) |
| `ttl` | `300` | Cache TTL in seconds |
| `auto_invalidate` | `True` | Whether writes automatically evict related cache entries |

### `ShadowCache.execute(sql, params=None)`

Execute a SQL statement with optional parameters. Returns `(cursor, rows)`.

- **SELECT**: checks Redis first. On hit returns `(None, cached_rows)`. On miss
  executes against MySQL, stores the result in Redis, and returns
  `(cursor, rows)`.
- **INSERT**: executes against MySQL. Returns `(cursor, None)`. Inspect
  `cursor.lastrowid` for the auto-generated ID.
- **UPDATE/DELETE**: executes against MySQL. Returns `(cursor, None)`. Inspect
  `cursor.rowcount` for the number of affected rows.
- **DDL and other statements**: forwarded to MySQL without caching.

### `ShadowCache.invalidate_table(table_name)`

Manually evict all cached entries for the given table. Returns the number of
Redis keys removed.

### `ShadowCache.flush_cache()`

Remove all ShadowCache keys from Redis. Returns the number of keys removed.

### `ShadowCache.stats`

Property returning a dict with `hits`, `misses`, `total_requests`, and
`hit_ratio`.

### `ShadowCache.close()`

Close the wrapped database connection.

## Prometheus Metrics

Enable metrics by calling `start_metrics_server()` before executing queries:

```python
from shadowcache.metrics import start_metrics_server

start_metrics_server(port=8000)

# Metrics are now exposed at http://localhost:8000/metrics
# Metrics tracked:
#   shadowcache_cache_hits_total    -- Counter
#   shadowcache_cache_misses_total  -- Counter
#   shadowcache_db_query_time_seconds -- Histogram
```

An example Prometheus scrape configuration is included in
`example_prometheus.yml`.

## Configuration With .env

Copy `.env.example` to `.env` and set your credentials:

```
REDIS_HOST=localhost
REDIS_PORT=6379
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_db_user
MYSQL_PASSWORD=your_db_password
MYSQL_DATABASE=your_database
LOG_LEVEL=INFO
```

## Running Tests

```bash
# Unit tests (no Redis or MySQL needed)
python -m pytest tests/test_parser.py tests/test_core.py tests/test_metrics.py -v

# Integration tests (requires Redis and MySQL)
python -m pytest tests/ -v
```

## License

MIT
