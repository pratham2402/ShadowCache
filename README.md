# ShadowCache

ShadowCache is a smart caching system designed to enhance database query performance by caching frequently accessed data using Redis. When data is not found in the Redis cache, the system retrieves it from the MySQL database and stores it in the cache for future use. The project also integrates Prometheus for monitoring cache hits, misses, and MySQL query execution time.

## Features

- **Redis Cache**: Uses Redis to cache database queries and improves retrieval speed.
- **MySQL Database**: Retrieves data from a MySQL database when the cache miss occurs.
- **Prometheus Integration**: Exposes metrics for monitoring cache hits, misses, and database query times.
- **Logging**: Provides detailed logging for debugging and tracking cache operations.

## Prerequisites

- Python 3.6+
- Docker (for Redis)
- MySQL Database
- Prometheus for metrics monitoring

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/yourusername/ShadowCache.git
   cd ShadowCache

2. **Create a Virtual Environment (optional but recommended)**:

    python3 -m venv redis-env
    source redis-env/bin/activate  # On Windows: redis-env\Scripts\activate

3. **Install dependencies.**:

    pip install -r requirements.txt

4. **Set up redis and MySQL**:

    Redis: You can run Redis using Docker:

        docker run --name shadowcache-redis -p 6379:6379 -d redis

    MySQL: Configure your MySQL database by updating the .env file with the correct credentials.

5. **Configure Prometheus.**:

    Ensure Prometheus is scraping the /metrics endpoint. Example configuration is included in the example_prometheus.yml file.

6. **Run the application**:

    Start the application by running:

        python cache_system.py

    The application will prompt you to enter a table name, key column, and key value for querying the data.

7. **Access prometheus.**:

    Visit http://localhost:8000 to view the Prometheus metrics for cache performance.

    View your Prometheus server for the cache hit/miss statistics.

## Configuration

    Redis: Set the Redis host and port in the .env file.

    MySQL: Set the MySQL credentials and database details in the .env file.

    Logging: The application logs operations to shadowcache.log.

## Example Usage

Once the app is running, you'll be prompted to input:

    Table name: For example, salaries.

    Key column name: For example, salary.
    
    Key value: For example, 52000.

After entering the details, the application will check the Redis cache. If the data is not found, it will fetch it from the MySQL database and cache it for future queries.