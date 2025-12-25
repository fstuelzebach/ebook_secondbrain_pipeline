import os
import json
from pathlib import Path
from typing import Optional, List

import requests
from dotenv import load_dotenv
from tqdm import tqdm


# -----------------------------
# Paths
# -----------------------------
ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"

if not CLEAN_DIR.exists():
    raise RuntimeError("Clean directory not found")


# -----------------------------
# Environment
# -----------------------------
load_dotenv(ROOT / ".env")

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


# -----------------------------
# EXPLICIT JSON → NOTION MAPPING
# -----------------------------
BOOK_TO_NOTION_MAP = {
    "stock_market_wizards__jack_d_schwager.json":
        "Stock Market Wizards",

    "the_mental_game_of_trading__jared_tendler.json":
        "The Mental Game of Trading",
}


# -----------------------------
# Notion helpers
# -----------------------------
def find_page_id(page_title: str) -> Optional[str]:
    payload = {
        "filter": {
            "property": "Title",
            "title": {"equals": page_title}
        }
    }

    res = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=HEADERS,
        json=payload,
    )
    res.raise_for_status()

    results = res.json().get("results", [])
    return results[0]["id"] if results else None


def append_blocks(page_id: str, blocks: List[dict]):
    for i in range(0, len(blocks), 100):
        batch = blocks[i:i + 100]
        res = requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=HEADERS,
            json={"children": batch},
        )
        res.raise_for_status()


# -----------------------------
# Main loop
# -----------------------------
for json_name, notion_title in tqdm(BOOK_TO_NOTION_MAP.items(), desc="Books"):
    json_path = CLEAN_DIR / json_name
    if not json_path.exists():
        print(f"❌ JSON not found: {json_name}")
        continue

    with open(json_path, "r", encoding="utf-8") as f:
        book = json.load(f)

    page_id = find_page_id(notion_title)
    if not page_id:
        print(f"❌ Notion page not found: {notion_title}")
        continue

    blocks = []

    for chapter in book.get("annotations", []):
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": chapter["chapter"]}}]
            }
        })

        for entry in chapter["entries"]:
            text = entry["highlight"] or ""
            if entry.get("note"):
                text += f"\nNote: {entry['note']}"

            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            })

    append_blocks(page_id, blocks)
    print(f"✅ Updated Notion page: {notion_title}")

print("🎉 All done.")
