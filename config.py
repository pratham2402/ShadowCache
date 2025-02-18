import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Redis Configuration
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "decode_responses": os.getenv("REDIS_DECODE_RESPONSES", "True") == "True",
}

# MySQL Configuration
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "default_user"),
    "password": os.getenv("MYSQL_PASSWORD", "default_password"),
    "database": os.getenv("MYSQL_DATABASE", "default_db"),
}
