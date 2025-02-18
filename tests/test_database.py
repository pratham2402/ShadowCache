import pytest
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import connect_to_db, fetch_from_db, insert_or_update_db, close_db_connection


@pytest.fixture(scope="module")
def db_connection():
    """Fixture to establish and close DB connection for all tests."""
    connection = connect_to_db()
    yield connection
    close_db_connection(connection)

def test_connect_to_db(db_connection):
    """Test database connection is successful."""
    assert db_connection is not None

def test_fetch_existing_record(db_connection):
    """Test fetching existing record from MySQL."""
    start_time = time.time()
    result = fetch_from_db("salaries", "salary", 52000, db_connection)
    execution_time = time.time() - start_time

    assert isinstance(result, list)
    assert execution_time < 1.0  # Ensure query is fast (adjust if needed)

def test_fetch_non_existing_record(db_connection):
    """Test fetching non-existing record should return empty list."""
    result = fetch_from_db("salaries", "salary", -1, db_connection)
    assert isinstance(result, list)
    assert len(result) == 0

def test_insert_or_update_db(db_connection):
    """Test inserting/updating a record and rollback after test."""
    test_emp_no = 99999  # Ensure a unique ID
    data = {"salary": 60000, "emp_no": test_emp_no}

    # Rollback any previous transaction to avoid conflicts
    db_connection.rollback()  # Add this line

    success = insert_or_update_db("salaries", data, "emp_no", test_emp_no, db_connection)
    assert success is True
