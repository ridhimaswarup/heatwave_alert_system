"""
config.py - application configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


# Load .env from the same folder as this file
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


# PostgreSQL configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "heatwavealertsystem")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))


# Flask configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")


if not DB_PASSWORD:
    raise RuntimeError(
        "DB_PASSWORD is missing from the .env file."
    )