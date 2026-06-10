"""Tests for shadowcache.parser."""

import pytest

from shadowcache.parser import extract_tables, extract_write_type, is_select_query


class TestExtractTables:
    def test_simple_select(self):
        tables = extract_tables("SELECT * FROM users")
        assert tables == {"users"}

    def test_select_with_join(self):
        tables = extract_tables(
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        )
        assert tables == {"users", "orders"}

    def test_select_with_subquery(self):
        tables = extract_tables(
            "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > 100)"
        )
        assert tables == {"users", "orders"}

    def test_insert(self):
        tables = extract_tables(
            "INSERT INTO products (name, price) VALUES (%s, %s)"
        )
        assert tables == {"products"}

    def test_update(self):
        tables = extract_tables("UPDATE users SET name = %s WHERE id = %s")
        assert tables == {"users"}

    def test_delete(self):
        tables = extract_tables("DELETE FROM sessions WHERE expired = 1")
        assert tables == {"sessions"}

    def test_unparseable_returns_empty(self):
        tables = extract_tables("GARBAGE XYZ ABC !! @@@")
        assert tables == set()

    def test_empty_string(self):
        tables = extract_tables("")
        assert tables == set()


class TestExtractWriteType:
    def test_select(self):
        assert extract_write_type("SELECT * FROM t") is None

    def test_insert(self):
        assert extract_write_type("INSERT INTO t VALUES (1)") == "INSERT"

    def test_update(self):
        assert extract_write_type("UPDATE t SET x = 1") == "UPDATE"

    def test_delete(self):
        assert extract_write_type("DELETE FROM t WHERE x = 1") == "DELETE"

    def test_truncate(self):
        assert extract_write_type("TRUNCATE TABLE t") == "DELETE"

    def test_create_table(self):
        assert extract_write_type("CREATE TABLE t (id INT)") is None

    def test_alter_table(self):
        assert extract_write_type("ALTER TABLE t ADD COLUMN x INT") is None

    def test_drop_table(self):
        assert extract_write_type("DROP TABLE t") is None

    def test_unparseable(self):
        assert extract_write_type("!! not sql !!") is None


class TestIsSelectQuery:
    def test_select(self):
        assert is_select_query("SELECT 1") is True

    def test_describe(self):
        assert is_select_query("DESCRIBE users") is True

    def test_show(self):
        # sqlglot parses SHOW as a Command, not as Show.
        # That is fine -- SHOW queries are rarely worth caching.
        assert is_select_query("SHOW TABLES") is False

    def test_insert(self):
        assert is_select_query("INSERT INTO t VALUES (1)") is False

    def test_update(self):
        assert is_select_query("UPDATE t SET x = 1") is False
