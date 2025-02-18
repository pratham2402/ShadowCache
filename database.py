import mysql.connector
import time
import os
from logger import logger
from dotenv import load_dotenv
load_dotenv()  # Load the .env file


# Fetch database credentials from environment variables
DB_USER = os.getenv("MYSQL_USER", "default_user")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "default_password")
DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_PORT = os.getenv("MYSQL_PORT", 3306)
DB_NAME = os.getenv("MYSQL_DATABASE", "default_db")

# Connect to MySQL Database
def connect_to_db():
    try:
        cnx = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        logger.info("✅ Connected to MySQL database successfully.")
        return cnx
    except mysql.connector.Error as err:
        logger.error(f"❌ MySQL Connection Error: {err}")
        return None


# Fetch data from MySQL with error handling and performance tracking
def fetch_from_db(table_name, key_column, key_value, connection):
    if connection is None:
        logger.error("❌ Database connection is not established.")
        return None

    start_time = time.time()  # Start execution timer

    try:
        cur = connection.cursor(dictionary=True)
        query = f"SELECT * FROM {table_name} WHERE {key_column} = %s"
        cur.execute(query, (key_value,))
        result = cur.fetchall()
        cur.close()

        execution_time = time.time() - start_time
        if result:
            logger.info(f"✅ Fetched {len(result)} records from {table_name} where {key_column} = {key_value} (Time: {execution_time:.4f}s).")
        else:
            logger.warning(f"⚠️ No records found in {table_name} for {key_column} = {key_value} (Time: {execution_time:.4f}s).")

        return result if result else []
    except mysql.connector.Error as e:
        logger.error(f"❌ Database fetch error: {e}")
        return None


# Insert or Update data in MySQL
def insert_or_update_db(table_name, data, key_column, key_value, connection):
    if connection is None:
        logger.error("❌ Database connection is not established.")
        return False

    start_time = time.time()  # Start execution timer

    try:
        cur = connection.cursor()

        # Check if the record exists
        check_query = f"SELECT COUNT(*) FROM {table_name} WHERE {key_column} = %s"
        cur.execute(check_query, (key_value,))
        exists = cur.fetchone()[0] > 0

        if exists:
            # Update existing record
            set_clause = ", ".join([f"{col} = %s" for col in data.keys()])
            update_query = f"UPDATE {table_name} SET {set_clause} WHERE {key_column} = %s"
            values = tuple(data.values()) + (key_value,)
            cur.execute(update_query, values)
            logger.info(f"🔄 Updated record in {table_name} where {key_column} = {key_value}.")
        else:
            # Insert new record
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            values = tuple(data.values())
            cur.execute(insert_query, values)
            logger.info(f"🆕 Inserted new record into {table_name}.")

        connection.commit()
        cur.close()

        execution_time = time.time() - start_time
        logger.info(f"✅ Insert/Update operation completed in {execution_time:.4f}s.")

        return True
    except mysql.connector.Error as e:
        logger.error(f"❌ Database insert/update error: {e}")
        return False

# Close database connection
def close_db_connection(connection):
    try:
        if connection and connection.is_connected():
            connection.close()
            logger.info("✅ Database connection closed.")
    except Exception as e:
        logger.error(f"❌ Error closing the database connection: {e}")
