import redis
import json
import time
import os
from database import fetch_from_db, connect_to_db, close_db_connection
from logger import logger
from prometheus_client import start_http_server, Counter, Histogram
from dotenv import load_dotenv
load_dotenv() 

# Metrics for cache performance
CACHE_HITS = Counter('cache_hits', 'Total Cache Hits')
CACHE_MISSES = Counter('cache_misses', 'Total Cache Misses')
DB_QUERY_TIME = Histogram('db_query_time_seconds', 'Time taken for MySQL queries')

# Connect to Redis
def connect_to_redis():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    try:
        return redis.Redis(host=redis_host, port=6379, decode_responses=True)
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        return None

# Set data in cache with optional TTL (Default: 5 minutes)
def set_data_to_cache(redis_client, key, value, ttl=300):
    try:
        json_value = json.dumps(value, default=str)
        redis_client.set(key, json_value, ex=ttl)
    except Exception as e:
        logger.error(f"Redis set error: {e}")

# Get data from cache or fallback to MySQL
def get_data(redis_client, db_connection, table_name, key_column, key_value):
    if not table_name or not key_column or not key_value:
        logger.error("Table name, key column, or key value not provided!")
        return None
    
    cache_key = f"{table_name}:{key_value}"
    start_time = time.time()
    
    # Check cache first
    cached_value = redis_client.get(cache_key)
    if cached_value:
        CACHE_HITS.inc()  # Track cache hit
        logger.info(f"Cache HIT ✅ - Key: {cache_key} (Time: {time.time() - start_time:.4f}s)")
        return json.loads(cached_value)
    
    # Cache miss, fetch from MySQL
    CACHE_MISSES.inc()  # Track cache miss
    logger.warning(f"Cache MISS ❌ - Fetching from MySQL...")

    if not db_connection:
        logger.error("MySQL database connection is not available.")
        return None

    with DB_QUERY_TIME.time():  # Measure MySQL query time
        result = fetch_from_db(table_name, key_column, key_value, db_connection)
    
    if result:
        set_data_to_cache(redis_client, cache_key, result)
        logger.info(f"Fetched from MySQL and Cached (Time: {time.time() - start_time:.4f}s)")
        return result
    
    return None

# Main execution
if __name__ == "__main__":
    start_http_server(8000)  # Start Prometheus server to expose /metrics
    redis_client = connect_to_redis()
    db_connection = connect_to_db()

    while True:
        # Example dynamic input
        table_name = input("Enter table name: ")  # e.g., "salaries"
        key_column = input("Enter key column name: ")  # e.g., "salary"
        key_value = input("Enter key value: ")  # e.g., 52000
        
        data = get_data(redis_client, db_connection, table_name, key_column, key_value)
        print("Final Data:", data)
        
        # Ask user if they want to execute another query
        continue_query = input("Do you want to execute another query? (yes/no): ").strip().lower()
        if continue_query != 'yes':
            break
    
    close_db_connection(db_connection)

    # Keep the script running so Prometheus can scrape metrics
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
