from pathlib import Path

# -------------------------
# Project root = folder containing pyproject.toml
# -------------------------
ROOT = Path(__file__).resolve().parents[1]

# -------------------------
# Data directories
# -------------------------
DATA_DIR = ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DERIVED_DATA_DIR = DATA_DIR / "derived"
EXPORTS_DIR = DATA_DIR / "exports"

# -------------------------
# Ensure directories exist
# -------------------------
for p in (DATA_DIR, RAW_DATA_DIR, DERIVED_DATA_DIR, EXPORTS_DIR):
    p.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    print("ROOT:", ROOT)
    print("DATA_DIR:", DATA_DIR)
