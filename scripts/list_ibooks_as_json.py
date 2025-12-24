import sqlite3
from pathlib import Path
from datetime import datetime
import json
import shutil
import sys

# -----------------------------
# Project root & data directory
# -----------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = DATA_DIR / "epub_list.json"

# -----------------------------
# Original iBooks DB path
# -----------------------------
if sys.platform == "win32":
    ORIG_BOOK_DB_PATH = Path("C:/path/to/BKLibrary.sqlite")
else:
    ORIG_BOOK_DB_PATH = (
        Path.home()
        / "Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary/BKLibrary-1-091020131601.sqlite"
    )

BOOK_DB_PATH = RAW_DATA_DIR / ORIG_BOOK_DB_PATH.name

# -----------------------------
# Copy DB if newer
# -----------------------------
def copy_if_newer(src: Path, dst: Path):
    if not src.exists():
        raise FileNotFoundError(f"iBooks DB not found: {src}")
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
        print(f"Copied DB → {dst}")

copy_if_newer(ORIG_BOOK_DB_PATH, BOOK_DB_PATH)

# -----------------------------
# Load books from DB
# -----------------------------
conn = sqlite3.connect(BOOK_DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT
        ZASSETID,
        ZTITLE,
        ZAUTHOR
    FROM ZBKLIBRARYASSET
    WHERE ZTITLE IS NOT NULL
    ORDER BY ZTITLE COLLATE NOCASE;
""")

books = []
for asset_id, title, author in cursor.fetchall():
    books.append({
        "asset_id": asset_id,
        "title": title,
        "author": author or ""
    })

conn.close()

# -----------------------------
# Write JSON
# -----------------------------
output = {
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "book_count": len(books),
    "books": books
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ Wrote {len(books)} books to:")
print(f"   {OUTPUT_FILE}")
