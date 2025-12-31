from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / "data" / "clean"
RAW_DIR = ROOT / "data" / "raw"

FILENAME_DATE_PATTERN = re.compile(r"^(?P<date>\d{8})_kindle_annotations_raw\.txt$")
PAGE_PATTERN = re.compile(r"Seite\s+([\d\-]+)")
TIMESTAMP_PATTERN = re.compile(r"Hinzugefügt am (.+)$")
META_PREFIX = "- Deine Markierung"
SEPARATOR = "=========="


def extract_date_from_filename(path: Path) -> datetime:
    match = FILENAME_DATE_PATTERN.match(path.name)
    if not match:
        raise ValueError(path.name)
    return datetime.strptime(match.group("date"), "%Y%m%d")


def select_and_cleanup_raw_files(delete_old: bool = True) -> Path:
    dated_files = []

    for path in RAW_DIR.iterdir():
        if not path.is_file():
            continue
        try:
            file_date = extract_date_from_filename(path)
        except ValueError:
            continue
        dated_files.append((file_date, path))

    if not dated_files:
        raise FileNotFoundError("No valid Kindle raw annotation files found.")

    dated_files.sort(key=lambda x: x[0])
    newest_date, newest_file = dated_files[-1]

    if delete_old:
        for file_date, path in dated_files:
            if file_date < newest_date:
                path.unlink()

    return newest_file


def normalize_title(title: str) -> str:
    return title.lstrip("\ufeff").strip()


def normalize_timestamp(raw: str) -> str:
    """
    Donnerstag, 25. Dezember 2025 12:01:07
    -> 2025-12-25T12:01:07
    """
    _, rest = raw.split(",", 1)
    rest = rest.strip()

    day, month, year_time = rest.split(" ", 2)
    year, time = year_time.split(" ", 1)

    months = {
        "Januar": "01",
        "Februar": "02",
        "März": "03",
        "April": "04",
        "Mai": "05",
        "Juni": "06",
        "Juli": "07",
        "August": "08",
        "September": "09",
        "Oktober": "10",
        "November": "11",
        "Dezember": "12",
    }

    iso = f"{year}-{months[month]}-{day.zfill(2)}T{time}"
    return iso


def page_sort_key(page: Optional[str]) -> int:
    if not page:
        return float("inf")
    try:
        return int(page.split("-")[0])
    except ValueError:
        return float("inf")


def parse_kindle_annotations(text: str) -> Dict[str, List[Dict[str, str]]]:
    lines = [line.rstrip() for line in text.splitlines()]
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    i = 0
    while i < len(lines) - 2:
        title = normalize_title(lines[i])
        meta = lines[i + 1].strip()

        if not title or not meta.startswith(META_PREFIX):
            i += 1
            continue

        page_match = PAGE_PATTERN.search(meta)
        ts_match = TIMESTAMP_PATTERN.search(meta)

        page = page_match.group(1) if page_match else None
        timestamp = normalize_timestamp(ts_match.group(1)) if ts_match else None

        # annotation text starts after empty line
        j = i + 3
        annotation_lines = []

        while j < len(lines) and lines[j].strip():
            line = lines[j].strip()
            if (
                line == SEPARATOR
                or line == title
                or line.startswith(META_PREFIX)
            ):
                j += 1
                continue
            annotation_lines.append(line)
            j += 1

        annotation_text = "\n".join(annotation_lines).strip()

        if annotation_text:
            grouped[title].append(
                {
                    "text": annotation_text,
                    "page": page,
                    "timestamp": timestamp,
                }
            )

        i = j + 1

    for title, items in grouped.items():
        items.sort(key=lambda a: page_sort_key(a["page"]))

    return grouped


def main() -> None:
    raw_file = select_and_cleanup_raw_files(delete_old=True)

    raw_text = raw_file.read_text(encoding="utf-8")
    grouped = parse_kindle_annotations(raw_text)

    output_date = raw_file.name[:8]
    output_path = CLEAN_DIR / f"{output_date}_kindle_annotations_clean.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)

    print(f"✔ Selected raw file: {raw_file.name}")
    print(f"✔ Clean JSON written to: {output_path}")


if __name__ == "__main__":
    main()
