![Star Badge](https://img.shields.io/static/v1?label=%F0%9F%8C%9F&message=If%20Useful&style=style=flat&color=BC4E99)
![Open Source Love](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)
[![View My Profile](https://img.shields.io/badge/View-My_Profile-green?logo=GitHub)](https://github.com/pratham2402)
[![View Repositories](https://img.shields.io/badge/View-My_Repositories-blue?logo=GitHub)](https://github.com/pratham2402?tab=repositories)

![Python](https://img.shields.io/badge/python-3.8+-blue?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-mysql%20%7C%20redis-red)

# ShadowCache

![ShadowCache Banner](./README%20Banner%20Art.png)

**Write SQL. Get caching. Nothing else.**

ShadowCache wraps your MySQL connection and transparently caches SELECT results
in Redis. INSERT, UPDATE, or DELETE statements automatically evict affected cache
entries so your reads never serve stale data. No ORM. No boilerplate. No config.

---

## Table of Contents

- [The problem](#the-problem)
- [Features](#features)
- [Installation](#installation)
- [Quick start](#quick-start)
- [API reference](#api-reference)
- [Configuration](#configuration)
- [Running tests](#running-tests)
- [License](#license)

---

## The problem

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

**With ShadowCache:**

```python
# One line. Caching and invalidation are automatic.
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))
cursor, _ = cache.execute("UPDATE users SET name = %s WHERE id = %s", ("Alice", 42))
```

---

## Features

- **Zero-schema caching.** Works with any MySQL table, any query. No model
  definitions needed.
- **Write-triggered eviction.** INSERT, UPDATE, and DELETE statements
  automatically evict cached SELECT results for the same table.
- **TTL safety net.** Cached entries expire after a configurable time-to-live,
  so eventual consistency is guaranteed even when SQL parsing fails.
- **Graceful fallback.** If Redis is unreachable, queries still execute
  against MySQL.

---

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

**Dependencies:** Python 3.8+, Redis, MySQL.

---

## Quick start

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

# Cold miss: hits MySQL, stores in Redis.
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))
for row in rows:
    print(row["name"])

# Warm hit: returns from Redis instantly.
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))

# Write evicts the cache.
cache.execute("UPDATE users SET name = %s WHERE id = %s", ("Alice", 42))

# Cache was evicted: fresh data from MySQL.
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))
```

---

## API reference

### Constructor

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
| `db_connection` | (required) | An open DB-API2 MySQL connection |
| `redis_client` | `None` | Pre-configured `redis.Redis` instance; created automatically if omitted |
| `redis_host` | `"localhost"` | Redis hostname |
| `redis_port` | `6379` | Redis port |
| `ttl` | `300` | Cache TTL in seconds |
| `auto_invalidate` | `True` | Whether writes automatically evict related cache entries |

### `execute(sql, params=None)`

Execute a SQL statement. Returns `(cursor, rows)`.

| SQL type | Behaviour |
|---|---|
| `SELECT` | Checks Redis first. Hit: returns `(None, cached_rows)`. Miss: executes on MySQL, caches result, returns `(cursor, rows)`. |
| `INSERT` | Executes on MySQL. Returns `(cursor, None)`. Use `cursor.lastrowid`. |
| `UPDATE` / `DELETE` | Executes on MySQL, evicts cache entries for affected tables. Returns `(cursor, None)`. Use `cursor.rowcount`. |
| DDL / other | Executes on MySQL without caching or eviction. |

### `invalidate_table(table_name)`

Manually evict all cached entries for the given table. Returns the count of Redis
keys removed.

### `flush_cache()`

Remove all ShadowCache keys from Redis. Returns the count of keys removed.

### `stats`

Property returning a dict: `hits`, `misses`, `total_requests`, `hit_ratio`.

### `close()`

Close the wrapped database connection.

---

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

---

## Running tests

```bash
# Unit tests (no Redis or MySQL needed -- all mocks)
python -m pytest tests/ -v
```

---

## License

MIT
