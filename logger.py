import logging
import os
from dotenv import load_dotenv
load_dotenv() 

# Get log level from environment variable (default: INFO)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Create logger
logger = logging.getLogger("ShadowCache")
logger.setLevel(LOG_LEVEL)

# Log format
log_format = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
)

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)

# File Handler (logs stored in 'shadowcache.log')
file_handler = logging.FileHandler("shadowcache.log")
file_handler.setFormatter(log_format)
logger.addHandler(file_handler)
