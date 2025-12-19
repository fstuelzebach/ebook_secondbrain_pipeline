import pandas as pd
from scripts.doctor import ROOT
from ibooks_notion_pipeline.paths import RAW_DATA_DIR, DERIVED_DATA_DIR
from ibooks_notion_pipeline.config import DB_RAW_PATTERN, BOOKS_DB
from pathlib import Path
import json
import sqlite3

SUMMARY_DIR = DERIVED_DATA_DIR
SUMMARY_DIR.mkdir(exist_ok=True)

def load_annotations():
    db_file = next(RAW_DATA_DIR.glob("AEAnnotation*.sqlite"), None)
    if not db_file:
        print("No annotations DB found!")
        return pd.DataFrame()
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query("SELECT * FROM ZAEANNOTATION", conn)
    conn.close()
    return df

def load_books():
    if not BOOKS_DB.exists():
        print("Books DB not found!")
        return pd.DataFrame()
    conn = sqlite3.connect(BOOKS_DB)
    df = pd.read_sql_query("SELECT * FROM ZBKLIBRARYASSET", conn)
    conn.close()
    return df

def main():
    annotations = load_annotations()
    books = load_books()
    print(f"Loaded {len(books)} books and {len(annotations)} annotations")

if __name__ == "__main__":
    main()
