from pathlib import Path
from .paths import DATA_DIR, RAW_DATA_DIR, DERIVED_DATA_DIR, EXPORTS_DIR

# Notion config (load from env if needed)
import os

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Other configs
DB_RAW_PATTERN = RAW_DATA_DIR / "AEAnnotation*.sqlite"
BOOKS_DB = RAW_DATA_DIR / "BKLibrary-1-091020131601.sqlite"

# Fallback for missing data
DEFAULT_AUTHOR = "Unknown"
DEFAULT_TITLE = "Unknown"
