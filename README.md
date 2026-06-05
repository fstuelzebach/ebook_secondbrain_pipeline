# ebook_secondbrain_pipeline

Sync e-book highlights and annotations into Notion — building a searchable "second brain" of your reading, one Notion page per book.

The pipeline ingests from **two sources** (Apple iBooks and Kindle), normalizes the annotations into a common JSON shape, and pushes them into a Notion database as page content.

> **Status:** personal project, actively being refactored. It works for the author's setup, but a clean checkout will not run end-to-end without the fixes listed under [Known issues / WIP](#known-issues--wip). Read that section before assuming `poetry install` is enough.

---

## What it does

```
 ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────┐
 │  iBooks DBs │     │   data/raw  │     │ data/clean  │     │  Notion  │
 │  (SQLite)   │ ──▶ │  (extract)  │ ──▶ │   (JSON)    │ ──▶ │ database │
 │  Kindle txt │     │             │     │             │     │          │
 └─────────────┘     └─────────────┘     └─────────────┘     └──────────┘
      sources            stage 1            stage 2            stage 3
                        extract / copy      normalize           export
```

The canonical intermediate format lives in `data/clean/` as per-book JSON; everything downstream reads from there.

### Source 1 — Apple iBooks

Apple Books stores its data in two local SQLite databases:

- `BKLibrary-*.sqlite` — book metadata (`ZASSETID`, `ZTITLE`, `ZAUTHOR`)
- `AEAnnotation-*.sqlite` — highlights and notes

The extractor copies these out of the macOS container into `data/raw/` (copy-if-newer), reads them, converts Apple's Cocoa-epoch timestamps (seconds since 2001-01-01) to ISO datetimes, filters to a focus list of titles, groups highlights by chapter, and writes one JSON file per book to `data/clean/`.

> **Platform note:** the iBooks source paths are macOS-only (`~/Library/Containers/com.apple.iBooksX/...`). The Windows branch in the code is a placeholder and not wired up.

### Source 2 — Kindle

`kindle_cleaner.py` parses a Kindle "My Clippings" style export (currently tuned to the **German** locale: `Seite`, `Hinzugefügt am`, `- Deine Markierung`, German month names). It picks the newest dated raw file, parses highlights grouped by book title with page and timestamp, and writes a clean JSON to `data/clean/`.

Expected raw filename pattern:

```
YYYYMMDD_kindle_annotations_raw.txt   →   YYYYMMDD_kindle_annotations_clean.json
```

### Export to Notion

`json_to_notion_page.py` maps each clean JSON file to a Notion page (via an explicit title map), finds the page by its `Title` property (using normalized title matching), and appends the highlights as Notion blocks: a `heading_2` per chapter, then a paragraph per highlight (with any attached note appended). Block writes are batched in groups of 100 and back off on HTTP 429.

---

## Project structure

```
ebook_secondbrain_pipeline/
├── ebook_secondbrain_pipeline/      # main package
│   ├── __init__.py
│   ├── __main__.py                  # runnable entry stub (prints paths)
│   ├── config.py                    # Notion config + DB path patterns
│   ├── epub_parser.py               # iBooks extractor (SQLite → clean JSON)
│   ├── kindle_cleaner.py            # Kindle clippings parser → clean JSON
│   ├── json_to_notion_page.py       # clean JSON → Notion pages
│   ├── paths.py                     # central path / data-dir definitions
│   └── utils_books.py               # title normalization, fuzzy match, focus list
├── scripts/                         # utilities + one-off exploration (see below)
├── docs/                            # architecture notes (currently stale)
├── data/                            # local DBs, raw, clean, exports (gitignored)
├── pyproject.toml
├── poetry.lock
└── README.md
```

> Despite its name, `epub_parser.py` does **not** parse EPUB files — it reads the iBooks annotation SQLite DBs. Actual EPUB handling lives in `scripts/epub_to_pdf.py`. (Rename is on the WIP list.)

### `scripts/` — what's reusable vs. scratch

This folder is a mix. Treat it accordingly:

| Script | Purpose | Keep? |
|---|---|---|
| `inspect_notion_schema.py` | Print the Notion database schema (property names/types) | Useful utility |
| `test_notion_connection.py` | Smoke-test API key + database access | Useful utility |
| `list_ibooks_as_json.py` | Dump all iBooks titles/authors to JSON | Useful utility |
| `inspect_ibooks.py` | Pandas-based iBooks summary with heuristic chapter assignment | Exploration |
| `epub_to_pdf.py` | Convert a single EPUB to PDF (ebooklib + weasyprint) | Standalone side-tool |
| `export_to_notion.py` | Dummy/stub export (writes placeholder data) | Stub — not a pipeline step |
| `inspect_and_update_summary.py` | Writes **random test text** into a page summary | Scratch — do not run on real data |
| `inspect_and_write_page.py` | Appends a TOC + placeholder headings to a page | Scratch |

---

## Requirements

- **Python 3.10+**
- **[Poetry](https://python-poetry.org/)** for dependency management
- **macOS** for the iBooks source (Apple Books DB paths)
- **`python_common`** — an external local shared library the author maintains, *not included in this repo*. It is wired as a Poetry path dependency (`../../python_common`), so clone it adjacent to this project:

  ```
  dev/
  └── projects/
      ├── ebook_secondbrain_pipeline/   ← this repo
      └── python_common/                ← clone here
  ```

> Several scripts pull in dependencies that are **not yet declared** in `pyproject.toml` (`tqdm`, `pandas`, `ebooklib`, `beautifulsoup4`, `weasyprint`). Until that's fixed, install them manually if you need those scripts. See [Known issues / WIP](#known-issues--wip).

---

## Setup

```bash
# 1. install
poetry install

# 2. configure Notion credentials
cp .env.example .env   # then fill in the values below
```

### Configuration (`.env`)

Create a `.env` file in the project root with:

```dotenv
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- `NOTION_API_KEY` — internal integration token from your Notion integration.
- `NOTION_DATABASE_ID` — the target database. It must have a `Title` property (and, for the inspect scripts, a `Summary` rich-text property).
- The Notion integration must be **shared with** the target database, or queries return empty.

`data/` and `.env` are gitignored, so your DBs, exports, and secrets are never committed.

---

## Usage

There is no single orchestrator yet — run the stages in order.

**1. Verify the Notion side (optional but recommended):**

```bash
poetry run python scripts/test_notion_connection.py
poetry run python scripts/inspect_notion_schema.py
```

**2. Extract.**

iBooks:
```bash
poetry run python -m ebook_secondbrain_pipeline.epub_parser
# copies the Apple DBs into data/raw/, writes per-book JSON to data/clean/
```

Kindle:
```bash
# drop your export into data/raw/ as YYYYMMDD_kindle_annotations_raw.txt, then:
poetry run python -m ebook_secondbrain_pipeline.kindle_cleaner
```

**3. Export to Notion:**

```bash
poetry run python -m ebook_secondbrain_pipeline.json_to_notion_page
# matches data/clean/*.json to Notion pages by title and appends highlight blocks
```

### The focus list

Processing is restricted to an **allow-list of book titles** — edit it to match the books in your library that you actually want synced. Matching is done on normalized titles (lowercased, punctuation/parentheses stripped, whitespace collapsed) so minor metadata differences between sources still line up.

> The focus list currently exists in **two places** (`epub_parser.py` and `utils_books.py`) and they disagree. The intended home is `utils_books.py` (it already owns the normalization and matching logic); consolidating them is a WIP item.

---

## Known issues / WIP

These are the open items from the in-progress rename and cleanup. Roughly in priority order:

1. **Broken entry-point import.** `__main__.py` imports `from ibooks_notion_pipeline.paths import ...` — the old package name. Update to `ebook_secondbrain_pipeline`, otherwise `python -m ebook_secondbrain_pipeline` crashes.
2. **Stale `pyproject.toml`.** `packages = [{ include = "ibooks_notion_pipeline" }]` still references the old name; should be `ebook_secondbrain_pipeline`.
3. **Stale docs.** `docs/architecture.md` and `docs/architecture.txt` describe the old `ibooks_notion_pipeline` layout and reference a `models.py` that no longer exists.
4. **Env var split.** `config.py` reads `NOTION_TOKEN`; the rest of the codebase reads `NOTION_API_KEY`. Standardize on **`NOTION_API_KEY`** and update `config.py`.
5. **Duplicate focus lists.** Consolidate `FOCUS_BOOK_TITLES` into `utils_books.py` and have `epub_parser.py` import it.
6. **Undeclared dependencies.** Add `tqdm`, `pandas`, `ebooklib`, `beautifulsoup4`, and `weasyprint` to `pyproject.toml` (or split the heavier ones into an optional/extra group, since only some scripts need them).
7. **Inconsistent data dirs.** `paths.py` defines `data/derived/` and `data/exports/`, but the extractors actually write to `data/clean/`. Reconcile on `data/clean/` as the canonical intermediate.
8. **`epub_parser.py` bypasses `paths.py`.** It redefines its own `ROOT`/`CLEAN_DIR`/`LOG_DIR` instead of importing the central definitions. Wire it through `paths.py`.
9. **Misleading module name.** `epub_parser.py` parses iBooks SQLite, not EPUBs — consider renaming (e.g. `ibooks_extractor.py`).
10. **No orchestrator.** Consider a small CLI that chains extract → normalize → export instead of running three modules by hand.
11. **macOS `Icon` artifacts** are committed; add them to `.gitignore`.

---

## License

Personal project — no license specified.
