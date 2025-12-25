import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import re
import json
from collections import defaultdict
import shutil
import sys

# -----------------------------
# Project root & data directories
# -----------------------------
ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
LOG_DIR = DATA_DIR / "log"

for p in (RAW_DATA_DIR, CLEAN_DIR, LOG_DIR):
    p.mkdir(parents=True, exist_ok=True)

ERROR_LOG_FILE = LOG_DIR / f"error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"


# -----------------------------
# Focus list (ONLY these books)
# -----------------------------
FOCUS_BOOK_TITLES = [
    #"The Mental Game of Trading: A System for Solving Problems With Greed, Fear, Anger, Confidence, and Discipline",
    #"Stock Market Wizards",
    "Atomic Habits: Tiny Changes, Remarkable Results",
    "Deep Work"
]

# -----------------------------
# Original iBooks DB paths
# -----------------------------
if sys.platform == "win32":
    ORIG_BOOK_DB_PATH = Path("C:/path/to/BKLibrary.sqlite")
    ORIG_ANNOT_DB_PATH = Path("C:/path/to/AEAnnotation.sqlite")
else:
    ORIG_BOOK_DB_PATH = Path.home() / "Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary/BKLibrary-1-091020131601.sqlite"
    ORIG_ANNOT_DB_PATH = Path.home() / "Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/AEAnnotation_v10312011_1727_local.sqlite"

BOOK_DB_PATH = RAW_DATA_DIR / ORIG_BOOK_DB_PATH.name
ANNOT_DB_PATH = RAW_DATA_DIR / ORIG_ANNOT_DB_PATH.name


# -----------------------------
# Helpers
# -----------------------------
def log_error(msg: str):
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {msg}\n")
    print(f"ERROR: {msg}")


def copy_if_newer(src: Path, dst: Path):
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)


def cocoa_timestamp_to_datetime(ts):
    if ts is None:
        return None
    return datetime(2001, 1, 1) + timedelta(seconds=ts)


def normalize_string(value: str) -> str:
    """
    Strong normalization:
    - lowercase
    - remove punctuation
    - collapse whitespace
    """
    if not value:
        return ""
    value = value.lower()
    value = re.sub(r"\([^)]*\)", "", value)  # remove parentheses (ISBNs etc.)
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_filename(value: str) -> str:
    value = normalize_string(value)
    value = re.sub(r"\s+", "_", value)
    return value


# -----------------------------
# Normalize focus titles once
# -----------------------------
FOCUS_TITLES_NORMALIZED = {
    normalize_string(t) for t in FOCUS_BOOK_TITLES
}


# -----------------------------
# Sync raw DBs
# -----------------------------
copy_if_newer(ORIG_BOOK_DB_PATH, BOOK_DB_PATH)
copy_if_newer(ORIG_ANNOT_DB_PATH, ANNOT_DB_PATH)


# -----------------------------
# Load books
# -----------------------------
books = {}

conn = sqlite3.connect(BOOK_DB_PATH)
cur = conn.cursor()
cur.execute("SELECT ZASSETID, ZTITLE, ZAUTHOR FROM ZBKLIBRARYASSET;")

for asset_id, title, author in cur.fetchall():
    books[asset_id] = {
        "title": title or "Unknown Title",
        "author": author or "Unknown Author",
        "annotations": []
    }

conn.close()


# -----------------------------
# Load annotations
# -----------------------------
conn = sqlite3.connect(ANNOT_DB_PATH)
cur = conn.cursor()

cur.execute("""
    SELECT 
        ZANNOTATIONASSETID,
        ZANNOTATIONSELECTEDTEXT,
        ZANNOTATIONNOTE,
        ZANNOTATIONCREATIONDATE,
        ZANNOTATIONLOCATION
    FROM ZAEANNOTATION
""")

for asset_id, highlight, note, created, loc_text in cur.fetchall():
    if asset_id not in books:
        continue

    books[asset_id]["annotations"].append({
        "highlight": highlight,
        "note": note,
        "created": cocoa_timestamp_to_datetime(created),
        "loc_text": loc_text
    })

conn.close()


# -----------------------------
# Export JSONs (FOCUSED ONLY)
# -----------------------------
exported = 0
skipped = 0

for book in books.values():
    title = book["title"]
    title_norm = normalize_string(title)

    # 🔒 Focus filter
    if title_norm not in FOCUS_TITLES_NORMALIZED:
        skipped += 1
        continue

    if not book["annotations"]:
        log_error(f"No annotations found for focused book: {title}")
        continue

    author = book["author"]

    title_fn = normalize_filename(title)
    author_fn = normalize_filename(author)

    filename = f"{title_fn}__{author_fn}.json"
    out_path = CLEAN_DIR / filename

    chapter_map = defaultdict(list)

    for a in book["annotations"]:
        chapter = "Unknown Chapter"
        if a["loc_text"] and "[" in a["loc_text"]:
            chapter = a["loc_text"].split("[")[1].split("]")[0]

        chapter_map[chapter].append({
            "highlight": a["highlight"],
            "note": a["note"],
            "created": a["created"].isoformat() if a["created"] else None
        })

    json_data = {
        "meta": {
            "source_title": title,
            "source_author": author,
            "normalized_title": title_fn,
            "normalized_author": author_fn
        },
        "annotations": []
    }

    for chapter, entries in sorted(chapter_map.items()):
        json_data["annotations"].append({
            "chapter": chapter,
            "entries": sorted(entries, key=lambda x: x["created"] or "")
        })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON written: {out_path.name}")
    exported += 1


print("\n──────── SUMMARY ────────")
print(f"Focused titles      : {len(FOCUS_BOOK_TITLES)}")
print(f"Exported JSONs      : {exported}")
print(f"Skipped (not focus) : {skipped}")
print(f"Error log           : {ERROR_LOG_FILE}")
