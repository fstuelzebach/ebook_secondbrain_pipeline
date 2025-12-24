import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import re
import json
from collections import defaultdict
import shutil
import sys
from difflib import get_close_matches

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
# Helper functions
# -----------------------------
def log_error(msg: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"ERROR: {msg}")

def copy_if_newer(src: Path, dst: Path):
    if not src.exists():
        log_error(f"Source file not found: {src}")
        return False
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
        print(f"Copied {src.name} → {dst}")
    return True

def cocoa_timestamp_to_datetime(cocoa_ts):
    if cocoa_ts is None:
        return None
    return datetime(2001, 1, 1) + timedelta(seconds=cocoa_ts)

def normalize_title(title: str) -> str:
    return (
        title.lower()
        .strip()
        .replace("–", "-")
        .replace("—", "-")
    )

def normalize_chapter(chapter_name):
    match = re.search(r'(\d+)', chapter_name or "")
    if match:
        return f"Chapter {int(match.group(1)):02d}"
    return chapter_name or "Unknown Chapter"

def assign_heading_level(chapter_name: str) -> int:
    match = re.search(r'(\d+(\.\d+)*)', chapter_name or "")
    return min(match.group(1).count(".") + 1, 3) if match else 1

def safe_filename(name: str) -> str:
    return re.sub(r'[^\w\-_ ]', "_", name)

# -----------------------------
# Step 0: Ensure raw DB is up-to-date
# -----------------------------
if not copy_if_newer(ORIG_BOOK_DB_PATH, BOOK_DB_PATH):
    sys.exit(1)
if not copy_if_newer(ORIG_ANNOT_DB_PATH, ANNOT_DB_PATH):
    sys.exit(1)

# -----------------------------
# Step 1: Load books
# -----------------------------
books = {}
conn = sqlite3.connect(BOOK_DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT ZASSETID, ZTITLE, ZAUTHOR, ZPATH FROM ZBKLIBRARYASSET;")

for asset_id, title, author, path in cursor.fetchall():
    books[asset_id] = {
        "title": title,
        "norm_title": normalize_title(title),
        "author": author,
        "annotations": []
    }
conn.close()

# -----------------------------
# Step 2: Load annotations
# -----------------------------
conn = sqlite3.connect(ANNOT_DB_PATH)
cursor = conn.cursor()
cursor.execute("""
    SELECT 
        ZANNOTATIONASSETID,
        ZANNOTATIONSELECTEDTEXT,
        ZANNOTATIONNOTE,
        ZANNOTATIONCREATIONDATE,
        ZANNOTATIONLOCATION
    FROM ZAEANNOTATION
    WHERE ZANNOTATIONSELECTEDTEXT IS NOT NULL OR ZANNOTATIONNOTE IS NOT NULL;
""")

for asset_id, highlight, note, created, loc_text in cursor.fetchall():
    if asset_id in books:
        books[asset_id]["annotations"].append({
            "highlight": highlight,
            "note": note,
            "created": cocoa_timestamp_to_datetime(created),
            "loc_text": loc_text
        })
conn.close()

# -----------------------------
# Step 3: Focus titles (AUTHORITATIVE SOURCE)
# -----------------------------
FOCUS_BOOK_TITLES = [
    "Hedge Fund Market Wizards",
    "Quantitative Trading",
    "Alpha Trader",
    "The Mental Game of Trading: A System for Solving Problems With Greed, Fear, Anger, Confidence, and Discipline",
    "The little Book of Trading",
    "The Little Book of Common Sense Investing: The Only Way to Guarantee Your Fair Share of Stock Market Returns",
    "Principles for Dealing With the Changing World Order : Why Nations Succeed and Fail (9781982164799)",
    "The Psychology of Money: Timeless Lessons on Wealth, Greed, and Happiness",
    "The Mental Strategies of Top Traders",
    "Stock Market Wizards",
    "The Front Office",
    "Inside the House of Money",
    "Souverän Investieren mit Indexfonds & ETFs",
    "Quantitative Trading"
]

normalized_focus = {normalize_title(t): t for t in FOCUS_BOOK_TITLES}
library_titles = {b["norm_title"]: b for b in books.values()}

matched = {}
unmatched = []

# -----------------------------
# Step 4: Match focus → library
# -----------------------------
for norm_focus, original_focus in normalized_focus.items():
    if norm_focus in library_titles:
        matched[original_focus] = library_titles[norm_focus]
    else:
        unmatched.append(original_focus)

# -----------------------------
# Step 5: Export matched books
# -----------------------------
for focus_title, book in matched.items():
    if not book["annotations"]:
        log_error(f"No annotations found for book: {focus_title}")
        continue

    chapter_map = defaultdict(list)

    for annot in book["annotations"]:
        chapter = "Unknown Chapter"
        loc = annot.get("loc_text")
        if loc and "[" in loc and "]" in loc:
            chapter = loc.split("[")[1].split("]")[0]
        chapter = normalize_chapter(chapter)

        chapter_map[chapter].append({
            "highlight": annot["highlight"],
            "note": annot["note"],
            "created": annot["created"].isoformat() if annot["created"] else None
        })

    book_json = {
        "title": focus_title,
        "author": book.get("author", ""),
        "annotations": []
    }

    for chapter, entries in sorted(chapter_map.items()):
        book_json["annotations"].append({
            "chapter": chapter,
            "heading_level": assign_heading_level(chapter),
            "entries": sorted(entries, key=lambda x: x["created"] or "")
        })

    out_file = CLEAN_DIR / f"{safe_filename(focus_title)}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(book_json, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON written: {out_file}")

# -----------------------------
# Step 6: Fuzzy diagnostics (ONLY unmatched focus books)
# -----------------------------
print("\n📚 Focus-book diagnostics")
print("────────────────────────")

print(f"\n✅ Matched ({len(matched)}):")
for t in matched:
    print(f"  - {t}")

print(f"\n❌ Unmatched focus books ({len(unmatched)}):")
for title in unmatched:
    norm = normalize_title(title)
    suggestions = get_close_matches(
        norm,
        library_titles.keys(),
        n=3,
        cutoff=0.6
    )
    if suggestions:
        print(f"  - {title}")
        print(f"    ↳ possible matches:")
        for s in suggestions:
            print(f"       • {library_titles[s]['title']}")
    else:
        print(f"  - {title} (no close match found)")

print("\nDone.")
print(f"Error log: {ERROR_LOG_FILE}")
