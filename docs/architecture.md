# iBooks Notion Pipeline - Architecture

## Folder structure
- ibooks_notion_pipeline/: main Python package
- scripts/: helper scripts for inspection and export
- data/: local SQLite DBs, derived summaries, Notion exports
- docs/: documentation

## Overview
- Scan iBooks SQLite DBs
- Parse annotations and chapters
- Summarize per book
- Export to Notion
