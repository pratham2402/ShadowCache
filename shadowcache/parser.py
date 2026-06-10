"""SQL parsing utilities using sqlglot.

Extracts table names and statement type information from raw SQL
strings so the core module can decide whether to cache or invalidate.
"""

from typing import Optional, Set

import sqlglot
from sqlglot import exp

from shadowcache.logger import get_logger

_log = get_logger(__name__)

_WRITE_TYPES = frozenset({exp.Insert, exp.Update, exp.Delete})

_READ_TYPES = frozenset({
    exp.Select,
    exp.Describe,
    exp.Show,
})


def _get_root_expression(sql: str) -> Optional[exp.Expression]:
    """Parse *sql* and return the root AST node, or None on failure."""
    try:
        return sqlglot.parse_one(sql, error_level=sqlglot.ErrorLevel.IGNORE)
    except Exception:
        _log.debug("sqlglot could not parse: %s", sql[:120])
        return None


def extract_tables(sql: str) -> Set[str]:
    """Return the set of table names referenced in *sql*.

    Handles SELECT, INSERT, UPDATE, DELETE, TRUNCATE, JOINs,
    sub-queries, and schema-qualified names like ``shop.users``.

    Returns an empty set if the SQL cannot be parsed, so callers can
    safely fall back to TTL-based expiry.
    """
    root = _get_root_expression(sql)
    if root is None:
        return set()

    tables: Set[str] = set()
    for table_node in root.find_all(exp.Table):
        name = table_node.name
        if name:
            tables.add(name)
    return tables


def extract_write_type(sql: str) -> Optional[str]:
    """Determine the write category of *sql*.

    Returns
    -------
    ``"INSERT"``, ``"UPDATE"``, ``"DELETE"``, or ``None`` if the
    statement does not modify data (SELECT, SHOW, DDL, etc.).
    TRUNCATE is treated as a write (returns ``"DELETE"``).
    """
    root = _get_root_expression(sql)
    if root is None:
        return None

    root_type = type(root)

    if root_type is exp.Insert:
        return "INSERT"
    if root_type is exp.Update:
        return "UPDATE"
    if root_type in (exp.Delete, exp.TruncateTable):
        return "DELETE"

    return None


def is_select_query(sql: str) -> bool:
    """Return True if *sql* is a SELECT (or SELECT-like) statement."""
    root = _get_root_expression(sql)
    if root is None:
        return False
    return type(root) in _READ_TYPES
