"""Quick demo of ShadowCache.  Requires Redis and MySQL to be running."""

import mysql.connector
from shadowcache import ShadowCache

# Connect to MySQL
conn = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="root",
    database="test_db",
)

# Wrap with ShadowCache
cache = ShadowCache(conn, ttl=30)

# --- Cold miss: hits MySQL, stores in Redis ---
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (1,))
print("Cold miss:", rows)

# --- Warm hit: served from Redis, no MySQL call ---
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (1,))
print("Warm hit:", rows)

# --- Write evicts the cache ---
cursor, _ = cache.execute("UPDATE users SET name = %s WHERE id = %s", ("Alice2", 1))
print(f"Updated {cursor.rowcount} row(s)")

# --- Cache was evicted, so this is a miss again (fresh data) ---
cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (1,))
print("After eviction:", rows)

# --- Manual table invalidation ---
cache.invalidate_table("users")

# --- Manual cache flush ---
cache.flush_cache()

# --- Stats ---
print("\nCache stats:", cache.stats)

cache.close()
