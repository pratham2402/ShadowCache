<p align="center">
  <img src="https://img.shields.io/static/v1?label=%F0%9F%8C%9F&message=If%20Useful&style=flat&color=BC4E99">
  <img src="https://badges.frapsoft.com/os/v1/open-source.svg?v=103">
  <a href="https://github.com/pratham2402"><img src="https://img.shields.io/badge/View-My_Profile-green?logo=GitHub"></a>
  <a href="https://github.com/pratham2402?tab=repositories"><img src="https://img.shields.io/badge/View-My_Repositories-blue?logo=GitHub"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue?logo=python">
  <img src="https://img.shields.io/badge/license-MIT-green">
  <img src="https://img.shields.io/badge/platform-mysql%20%7C%20redis-red">
</p>

# ShadowCache

<p align="center">
  <img src="./README%20Banner%20Art.png" alt="ShadowCache Banner">
</p>

> **Write SQL. Get caching. Nothing else.**

ShadowCache wraps your MySQL connection and transparently caches SELECT results
in Redis. INSERT, UPDATE, or DELETE statements automatically evict affected cache
entries so your reads never serve stale data. No ORM. No boilerplate. No config.

<br>

<details open>
<summary><b>Table of Contents</b></summary>

- [The Problem](#the-problem)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Running Tests](#running-tests)
- [License](#license)

</details>

## The Problem

Every developer who writes raw SQL eventually writes this:

```python
# 8 lines of boilerplate for every cached query
cache_key = f"user:{user_id}"
cached = redis.get(cache_key)
if cached:
    return json.loads(cached)

cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
row = cursor.fetchone()
redis.set(cache_key, json.dumps(row), ex=300)
return row
```

And on every INSERT, UPDATE, or DELETE you need to remember:

```python
cursor.execute("UPDATE users SET name = %s WHERE id = %s", (name, user_id))
redis.delete(f"user:{user_id}")  # easy to forget, easy to get wrong
```

```diff
- Boilerplate for every query
- Manual invalidation you will forget
+ One line. Caching and invalidation are automatic.
```

**With ShadowCache:**

```python
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))
cursor, _ = cache.execute("UPDATE users SET name = %s WHERE id = %s", ("Alice", 42))
```

## Features

| | |
|---|---|
| **Zero-schema caching** | Works with any MySQL table, any query. No model definitions needed. |
| **Write-triggered eviction** | INSERT, UPDATE, and DELETE automatically evict cached SELECTs for the same table. |
| **TTL safety net** | Cached entries expire after a configurable time-to-live. Eventual consistency guaranteed. |
| **Graceful fallback** | If Redis is unreachable, queries still execute against MySQL. |

## Installation

```bash
pip install shadowcache
```

> Or install from source:

```bash
git clone https://github.com/pratham2402/ShadowCache.git
cd ShadowCache
pip install -r requirements.txt
```

**Requires:** Python 3.8+, Redis, MySQL.

## Quick Start

```python
import mysql.connector
from shadowcache import ShadowCache

conn = mysql.connector.connect(
    host="localhost", database="my_app",
    user="app_user", password="secret",
)

cache = ShadowCache(conn)

# Cold miss -- hits MySQL, stores in Redis
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))

# Warm hit -- returns from Redis instantly
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))

# Write evicts the cache
cache.execute("UPDATE users SET name = %s WHERE id = %s", ("Alice", 42))

# Cache was evicted -- fresh data from MySQL
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))
```

## API Reference

### `ShadowCache(db_connection, *, ...)`

```python
ShadowCache(
    db_connection,
    *,
    redis_client=None,
    redis_host="localhost",
    redis_port=6379,
    ttl=300,
    auto_invalidate=True,
)
```

| Parameter | Default | Description |
|---|---|---|
| `db_connection` | *(required)* | An open DB-API2 MySQL connection |
| `redis_client` | `None` | Pre-configured `redis.Redis` instance; created automatically if omitted |
| `redis_host` | `"localhost"` | Redis hostname |
| `redis_port` | `6379` | Redis port |
| `ttl` | `300` | Cache TTL in seconds |
| `auto_invalidate` | `True` | Whether writes automatically evict related cache entries |

### `ShadowCache.execute(sql, params=None)`

Returns `(cursor, rows)`.

| SQL | Behaviour |
|---|---|
| `SELECT` | Checks Redis first. Hit returns `(None, cached_rows)`. Miss executes on MySQL, caches, returns `(cursor, rows)`. |
| `INSERT` | Executes on MySQL. Returns `(cursor, None)`. See `cursor.lastrowid`. |
| `UPDATE` / `DELETE` | Executes on MySQL, evicts cache for affected tables. Returns `(cursor, None)`. See `cursor.rowcount`. |
| DDL / other | Executes on MySQL. No caching, no eviction. |

### Other Methods

| Method | Description |
|---|---|
| `invalidate_table(name)` | Evict all cached entries for a table. Returns count of keys removed. |
| `flush_cache()` | Remove all ShadowCache keys from Redis. Returns count of keys removed. |
| `stats` | Property. Returns `{"hits", "misses", "total_requests", "hit_ratio"}`. |
| `close()` | Close the wrapped database connection. |

## Configuration

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
# Unit tests -- no Redis or MySQL needed, all mocks
python -m pytest tests/ -v
```

## License

MIT
