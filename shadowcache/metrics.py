"""Prometheus instrumentation for ShadowCache.

Metrics are lazily initialised so that importing the package does not
immediately register collectors or start an HTTP server.  Call
:func:`start_metrics_server` explicitly when metrics are desired.
"""

CACHE_HITS = None
CACHE_MISSES = None
DB_QUERY_TIME = None

_server_started = False


def _init_metrics():
    """Create metric objects (idempotent)."""
    global CACHE_HITS, CACHE_MISSES, DB_QUERY_TIME

    if CACHE_HITS is not None:
        return  # already initialised

    from prometheus_client import REGISTRY, Counter, Histogram

    _hits_name = "shadowcache_cache_hits_total"
    _misses_name = "shadowcache_cache_misses_total"
    _db_time_name = "shadowcache_db_query_time_seconds"

    for name, factory, attr in [
        (_hits_name, Counter, "CACHE_HITS"),
        (_misses_name, Counter, "CACHE_MISSES"),
        (_db_time_name, Histogram, "DB_QUERY_TIME"),
    ]:
        try:
            collector = factory(
                name,
                f"ShadowCache {attr.lower().replace('_', ' ')}",
            )
        except ValueError:
            # Already registered in a previous call.
            collector = REGISTRY._names_to_collectors[name]
        if attr == "CACHE_HITS":
            CACHE_HITS = collector
        elif attr == "CACHE_MISSES":
            CACHE_MISSES = collector
        else:
            DB_QUERY_TIME = collector


def start_metrics_server(port: int = 8000) -> None:
    """Start a Prometheus HTTP metrics endpoint on *port*."""
    global _server_started

    _init_metrics()
    if _server_started:
        return

    from prometheus_client import start_http_server

    start_http_server(port)
    _server_started = True


def record_hit():
    """Increment the cache-hits counter (no-op when metrics are off)."""
    if CACHE_HITS is not None:
        CACHE_HITS.inc()


def record_miss():
    """Increment the cache-misses counter (no-op when metrics are off)."""
    if CACHE_MISSES is not None:
        CACHE_MISSES.inc()


def track_db_time():
    """Return a context manager for the DB_QUERY_TIME histogram, or a
    no-op when metrics are off."""
    if DB_QUERY_TIME is not None:
        return DB_QUERY_TIME.time()
    return _NoopContext()


class _NoopContext:
    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass
