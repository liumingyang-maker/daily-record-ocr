"""Application configuration settings."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STORAGE_DIR = DATA_DIR / "storage"
CONFIGS_DIR = BASE_DIR / "app" / "configs"

# Application settings
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8765"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.sqlite3'}")

# MIMO API
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")
MIMO_MODEL = os.getenv("MIMO_MODEL", "mimo-v2.5")

# Storage subdirectories
RAW_IMAGES_DIR = STORAGE_DIR / "raw_images"
CORRECTED_IMAGES_DIR = STORAGE_DIR / "corrected_images"
RECORD_CROPS_DIR = STORAGE_DIR / "record_crops"
CELL_CROPS_DIR = STORAGE_DIR / "cell_crops"
HISTORY_IMPORTS_DIR = STORAGE_DIR / "history_imports"
EXPORTS_DIR = STORAGE_DIR / "exports"
DEBUG_DIR = STORAGE_DIR / "debug"
BACKUPS_DIR = DATA_DIR / "backups"
