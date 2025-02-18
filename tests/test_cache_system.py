import sys
import os
import pytest
from unittest.mock import patch
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cache_system import connect_to_redis, set_data_to_cache, get_data
from database import close_db_connection, connect_to_db, fetch_from_db

@pytest.fixture(scope="function")
def redis_client():
    client = connect_to_redis()
    client.flushdb()
    yield client
    client.flushdb()


@pytest.fixture(scope="function")
def db_connection():
    """Mock MySQL database connection and cursor behavior."""
    with patch("database.connect_to_db") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Ensure the cursor() function returns the mock cursor
        mock_conn.cursor.return_value = mock_cursor

        # Mock fetchall() to return a list of records
        mock_cursor.fetchall.return_value = [{"salary": 52000, "emp_no": 12345}]

        # Mock fetchone() for insert_or_update_db (returning a count of existing records)
        mock_cursor.fetchone.return_value = (1,)  # Simulating 1 record found

        yield mock_conn


def test_connect_to_redis(redis_client):
    assert redis_client.ping() is True

def test_set_and_get_cache(redis_client):
    set_data_to_cache(redis_client, "test_key", "test_value", ttl=10)
    assert get_data(redis_client, None, None, None, "test_key") == "test_value"

def test_cache_expiry(redis_client):
    ttl = 3
    set_data_to_cache(redis_client, "temp_key", "temp_value", ttl=ttl)
    assert get_data(redis_client, None, None, None, "temp_key") == "temp_value"

@patch("database.fetch_from_db")
def test_get_data_cache_hit(mock_fetch, redis_client, db_connection):
    cache_key = "salaries:52000"
    redis_client.set(cache_key, "cached_result")
    
    result = get_data(redis_client, db_connection, "salaries", "salary", 52000)
    assert result == "cached_result"
    mock_fetch.assert_not_called()

@patch("cache_system.fetch_from_db")  # 👈 Patch where it is used, not where it is defined!
def test_get_data_cache_miss(mock_fetch, redis_client, db_connection):
    """Test get_data() when there is a cache miss, requiring a database fetch."""
    
    assert isinstance(mock_fetch, MagicMock), "Mocking failed for fetch_from_db"

    # Mock function return value
    mock_fetch.return_value = [{"salary": 52000, "emp_no": 12345}]

    result = get_data(redis_client, db_connection, "salaries", "salary", 52000)

    assert isinstance(result, list)
    assert result == [{"salary": 52000, "emp_no": 12345}]

    # Print actual call arguments to debug
    print("Mock fetch_from_db call arguments:", mock_fetch.call_args_list)

    # Ensure fetch_from_db was called with correct arguments
    mock_fetch.assert_called_once_with("salaries", "salary", 52000, db_connection)



