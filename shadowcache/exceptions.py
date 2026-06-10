"""Custom exceptions for ShadowCache."""


class ShadowCacheError(Exception):
    """Base exception for all ShadowCache errors."""


class CacheParseError(ShadowCacheError):
    """Raised when a SQL statement cannot be parsed by sqlglot.

    The original SQL is still executed against MySQL; only the caching
    or invalidation step is skipped.
    """


class CacheBackendError(ShadowCacheError):
    """Raised when Redis or MySQL is unreachable."""
