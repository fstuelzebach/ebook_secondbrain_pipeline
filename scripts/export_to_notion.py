from ibooks_notion_pipeline.config import NOTION_TOKEN, NOTION_DATABASE_ID
import json
from pathlib import Path

EXPORT_DIR = Path("./data/exports")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

def export_summary(summary, filename="notion_export.json"):
    out_path = EXPORT_DIR / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)
    print(f"📄 Exported to {out_path}")

def main():
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        print("⚠ Notion token or database ID missing in .env")
        return
    # Example dummy export
    summary = [{"book_id": "dummy", "title": "Dummy Book", "chapters": []}]
    export_summary(summary)

if __name__ == "__main__":
    main()
