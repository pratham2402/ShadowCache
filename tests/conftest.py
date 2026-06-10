"""Shared fixtures for ShadowCache tests."""

import os
import sys

import pytest

# Ensure the package under test is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def redis_host():
    return os.getenv("REDIS_HOST", "localhost")


@pytest.fixture
def mysql_config():
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "cache_user"),
        "password": os.getenv("MYSQL_PASSWORD", "Cache_user1"),
        "database": os.getenv("MYSQL_DATABASE", "test_db"),
    }
