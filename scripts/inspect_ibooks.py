# inspect_ibooks.py

import sqlite3
import pandas as pd
from pathlib import Path
import json

# -------------------------
# Constants & Folders
# -------------------------
DATA_DIR = Path("../data")
SUMMARY_DIR = DATA_DIR / "ibooks_summary"
SUMMARY_DIR.mkdir(exist_ok=True)

APPLE_EPOCH_START = pd.Timestamp("2001-01-01")

# -------------------------
# Load annotations
# -------------------------
def load_annotations(db_file=None):
    if db_file is None:
        db_file = next(DATA_DIR.glob("AEAnnotation*.sqlite"))
    conn = sqlite3.connect(db_file)

    table_info = conn.execute("PRAGMA table_info(ZAEANNOTATION)").fetchall()
    columns = [col[1] for col in table_info]

    select_cols = [
        "ZANNOTATIONSELECTEDTEXT AS highlight",
        "ZANNOTATIONSTYLE AS color",
        "ZANNOTATIONMODIFICATIONDATE AS modified",
        "ZANNOTATIONASSETID AS book_id"
    ]

    if "ZFUTUREPROOFING5" in columns:
        select_cols.append("ZFUTUREPROOFING5 AS chapter_fallback")
    if "ZANNOTATIONSTARTLOC" in columns:
        select_cols.append("ZANNOTATIONSTARTLOC AS start_loc")
    if "ZANNOTATIONENDLOC" in columns:
        select_cols.append("ZANNOTATIONENDLOC AS end_loc")

    query = f"SELECT {', '.join(select_cols)} FROM ZAEANNOTATION WHERE ZANNOTATIONSELECTEDTEXT IS NOT NULL"
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["book_id"] = df["book_id"].astype(str).str.strip()
    df["highlight"] = df["highlight"].astype(str).str.strip()
    df["modified"] = APPLE_EPOCH_START + pd.to_timedelta(df["modified"], unit="s", errors="coerce")

    for col in ["start_loc", "end_loc"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "chapter_fallback" in df.columns:
        df["chapter_fallback"] = df["chapter_fallback"].astype(str).str.strip()

    return df


# -------------------------
# Load books metadata
# -------------------------
def load_books(db_file=None):
    db_file = db_file or DATA_DIR / "BKLibrary-1-091020131601.sqlite"
    conn = sqlite3.connect(db_file)

    table_info = conn.execute("PRAGMA table_info(ZBKLIBRARYASSET)").fetchall()
    columns = [col[1] for col in table_info]

    select_cols = ["ZASSETID AS book_id", "ZTITLE AS title", "ZAUTHOR AS author"]
    if "ZDATEADDED" in columns:
        select_cols.append("ZDATEADDED AS date_added")
    if "ZDATEFINISHED" in columns:
        select_cols.append("ZDATEFINISHED AS date_finished")

    query = f"SELECT {', '.join(select_cols)} FROM ZBKLIBRARYASSET WHERE ZASSETID IS NOT NULL"
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["book_id"] = df["book_id"].astype(str).str.strip()
    df["title"] = df["title"].astype(str).str.strip().fillna("Unknown")
    df["author"] = df["author"].astype(str).str.strip().fillna("Unknown")

    for date_col in ["date_added", "date_finished"]:
        if date_col in df.columns:
            df[date_col] = APPLE_EPOCH_START + pd.to_timedelta(df[date_col], unit="s", errors="coerce")

    return df


# -------------------------
# Assign chapters more granularly
# -------------------------
def assign_chapters(df):
    """
    Assign chapters/subchapters using:
    - start_loc for ordering and detecting jumps
    - fallback chapter if start_loc missing
    """
    df = df.copy()
    if "start_loc" in df.columns:
        df = df.sort_values(["book_id", "start_loc"])
        # Create a chapter ID whenever there's a significant jump in start_loc
        df["chapter"] = None
        for book_id, book_df in df.groupby("book_id"):
            locs = book_df["start_loc"].fillna(0).values
            chapters = []
            chapter_counter = 1
            prev_loc = locs[0] if len(locs) > 0 else 0
            for loc in locs:
                # You can adjust the jump threshold (e.g., 500) for new chapters
                if loc - prev_loc > 500:
                    chapter_counter += 1
                chapters.append(f"Chapter {chapter_counter}")
                prev_loc = loc
            df.loc[book_df.index, "chapter"] = chapters
    elif "chapter_fallback" in df.columns:
        df = df.sort_values(["book_id", "chapter_fallback", "modified"])
        df["chapter"] = df["chapter_fallback"].fillna("Unknown")
    else:
        df["chapter"] = "Unknown"

    return df


# -------------------------
# Summarize annotations by book and chapter
# -------------------------
def summarize_annotations(annotations, books):
    annotations = assign_chapters(annotations)
    merged = annotations.merge(books, on="book_id", how="left")
    merged["title"] = merged["title"].fillna("Unknown")
    merged["author"] = merged["author"].fillna("Unknown")

    summary_list = []
    for book_id, book_df in merged.groupby("book_id"):
        book_meta = {
            "book_id": book_id,
            "title": book_df["title"].iloc[0],
            "author": book_df["author"].iloc[0],
            "date_added": (book_df["date_added"].iloc[0].isoformat()
                           if "date_added" in book_df.columns and pd.notnull(book_df["date_added"].iloc[0])
                           else None),
            "date_finished": (book_df["date_finished"].iloc[0].isoformat()
                              if "date_finished" in book_df.columns and pd.notnull(book_df["date_finished"].iloc[0])
                              else None),
            "chapters": []
        }

        for chap, chap_df in book_df.groupby("chapter"):
            chapter_summary = {
                "chapter": chap,
                "highlights_count": int(chap_df.shape[0]),
                "colors_used": sorted(chap_df["color"].dropna().unique().tolist()),
                "first_highlight": (chap_df["modified"].min().isoformat() if pd.notnull(chap_df["modified"].min()) else None),
                "last_highlight": (chap_df["modified"].max().isoformat() if pd.notnull(chap_df["modified"].max()) else None)
            }
            book_meta["chapters"].append(chapter_summary)

        summary_list.append(book_meta)

    return summary_list


# -------------------------
# Save summary JSON
# -------------------------
def save_summary_json(summary_list, filename="books_summary.json"):
    out_path = SUMMARY_DIR / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary_list, f, indent=4, ensure_ascii=False)
    print(f"📄 Summary saved to {out_path}")


# -------------------------
# Main
# -------------------------
def main():
    annotations = load_annotations()
    books = load_books()
    summary = summarize_annotations(annotations, books)
    save_summary_json(summary)
    print("✔ Done! JSON summary is ready for Notion export.")


if __name__ == "__main__":
    main()
