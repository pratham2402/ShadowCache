"""ShadowCache -- Transparent Redis caching for raw SQL connections.

Usage:
    import mysql.connector
    from shadowcache import ShadowCache

    conn = mysql.connector.connect(host="localhost", database="mydb")
    cache = ShadowCache(conn)

    # SELECTs are transparently cached
    cursor, rows = cache.execute("SELECT * FROM users WHERE id = %s", (42,))

    # INSERT/UPDATE/DELETE automatically evict related cache entries
    cache.execute("UPDATE users SET name = %s WHERE id = %s", ("Alice", 42))
"""

from shadowcache.exceptions import ShadowCacheError

__all__ = ["ShadowCacheError"]
__version__ = "0.1.0"


def __getattr__(name):
    """Lazily import ShadowCache so the package is usable even when
    only a subset of modules have been installed."""
    if name == "ShadowCache":
        from shadowcache.core import ShadowCache as _sc

        return _sc
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

