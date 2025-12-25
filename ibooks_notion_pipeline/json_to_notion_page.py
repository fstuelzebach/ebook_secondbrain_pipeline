import os
import json
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from tqdm import tqdm

from utils_books import normalize_title

# -----------------------------
# Paths
# -----------------------------
ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"

if not CLEAN_DIR.exists():
    raise RuntimeError(f"Clean directory not found: {CLEAN_DIR}")

# -----------------------------
# Environment
# -----------------------------
load_dotenv(ROOT / ".env")

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_API_KEY or not NOTION_DATABASE_ID:
    raise ValueError("Missing NOTION_API_KEY or NOTION_DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# -----------------------------
# Explicit JSON → Notion mapping
# -----------------------------
BOOK_TO_NOTION_MAP = {
    "stock_market_wizards__jack_d_schwager.json": "Stock Market Wizards",
    "the_mental_game_of_trading_a_system_for_solving_problems_with_greed_fear_anger_confidence_and_discipline__jared_tendler.json": "The Mental Game of Trading",
}

# -----------------------------
# Notion-safe rich text
# -----------------------------
def rt(text: str) -> dict:
    return {
        "type": "text",
        "text": {"content": text},
        "annotations": {
            "bold": False,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": "default",
        },
    }

# -----------------------------
# Notion helpers
# -----------------------------
def find_notion_page_id(page_title: str) -> Optional[str]:
    start_cursor = None
    normalized_target = normalize_title(page_title)

    while True:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        res = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
            headers=HEADERS,
            json=payload,
        )
        res.raise_for_status()
        data = res.json()

        for page in data.get("results", []):
            title_prop = page["properties"].get("Title", {}).get("title", [])
            if not title_prop:
                continue

            notion_title = title_prop[0]["plain_text"]
            if normalize_title(notion_title) == normalized_target:
                return page["id"]

        if not data.get("has_more"):
            break

        start_cursor = data.get("next_cursor")

    return None


def append_blocks(parent_block_id: str, blocks: list[dict], label: str):
    batches = [blocks[i:i + 100] for i in range(0, len(blocks), 100)]

    for batch in tqdm(batches, desc=f"Appending blocks for '{label}'", unit="batch"):
        while True:
            res = requests.patch(
                f"https://api.notion.com/v1/blocks/{parent_block_id}/children",
                headers=HEADERS,
                json={"children": batch},
            )
            if res.status_code == 429:
                import time
                time.sleep(int(res.headers.get("Retry-After", 1)))
                continue
            res.raise_for_status()
            break

# -----------------------------
# Main
# -----------------------------
json_files = list(BOOK_TO_NOTION_MAP.keys())
print(f"📚 Processing {len(json_files)} book(s).")

for json_name in tqdm(json_files, desc="Books", unit="book"):
    json_path = CLEAN_DIR / json_name
    if not json_path.exists():
        raise RuntimeError(f"JSON not found: {json_name}")

    with open(json_path, "r", encoding="utf-8") as f:
        book = json.load(f)

    notion_page_title = BOOK_TO_NOTION_MAP[json_name]
    print(f"🔎 Looking for Notion page: {notion_page_title}")

    page_id = find_notion_page_id(notion_page_title)
    if not page_id:
        raise RuntimeError(
            f"❌ No Notion page found for '{notion_page_title}'. "
            f"Check database ID and Title property."
        )

    blocks = []

    for chapter in book.get("annotations", []):
        raw = (chapter.get("chapter") or "").strip()
        chapter_title = raw if raw and not raw.lower().startswith(("bm", "cfi", "xhtml", "unknown")) else "Chapter"

        blocks.append({
            "type": "heading_2",
            "heading_2": {"rich_text": [rt(chapter_title)]}
        })

        for entry in chapter.get("entries", []):
            text = entry.get("highlight") or ""
            if entry.get("note"):
                text += f"\nNote: {entry['note']}"

            if text.strip():
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {"rich_text": [rt(text)]}
                })

    if not blocks:
        print(f"⚠️ No blocks generated for '{notion_page_title}'")
        continue

    append_blocks(page_id, blocks, notion_page_title)

    print(f"✅ Updated Notion page: {notion_page_title}")

print("🎉 All done.")
