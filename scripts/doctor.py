from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PATHS = [
    "pyproject.toml",
    "poetry.lock",
    "README.md",
    ".gitignore",
    ".env.example",
    "ibooks_notion_pipeline/__init__.py",
    "ibooks_notion_pipeline/config.py",
    "ibooks_notion_pipeline/paths.py",
    "ibooks_notion_pipeline/__main__.py",
    "scripts/inspect_library.py",
    "scripts/inspect_single_book.py",
    "scripts/export_to_notion.py",
    "docs/architecture.md",
    "data",
]

def main():
    print("\n📁 Project root:")
    print(f"   {ROOT}\n")

    print("=== EXPECTED PATHS ===")
    for rel in EXPECTED_PATHS:
        p = ROOT / rel
        status = "OK" if p.exists() else "MISSING"
        print(f"[{status:<7}] {rel}")

    print("\n=== TOP-LEVEL CONTENTS ===")
    for p in sorted(ROOT.iterdir()):
        kind = "📂" if p.is_dir() else "📄"
        print(f"{kind} {p.name}")

if __name__ == "__main__":
    main()
