# inspect_single_book.py

import sqlite3
import pandas as pd
from pathlib import Path
import json

DATA_DIR = Path("../data")
SUMMARY_DIR = DATA_DIR / "ibooks_summary"
SUMMARY_DIR.mkdir(exist_ok=True)


def load_annotations(db_file=None):
    db_file = db_file or next(DATA_DIR.glob("AEAnnotation*.sqlite"))
    conn = sqlite3.connect(db_file)

    # Detect available columns
    table_info = conn.execute("PRAGMA table_info(ZAEANNOTATION)").fetchall()
    columns = [col[1] for col in table_info]

    select_cols = [
        "ZANNOTATIONSELECTEDTEXT AS highlight",
        "ZANNOTATIONSTYLE AS color",
        "ZANNOTATIONMODIFICATIONDATE AS modified",
        "ZANNOTATIONASSETID AS book_id"
    ]

    if "ZFUTUREPROOFING5" in columns:
        select_cols.append("ZFUTUREPROOFING5 AS chapter_name")
    if "ZANNOTATIONSTARTLOC" in columns:
        select_cols.append("ZANNOTATIONSTARTLOC AS start_loc")
        select_cols.append("ZANNOTATIONENDLOC AS end_loc")

    query = f"SELECT {', '.join(select_cols)} FROM ZAEANNOTATION WHERE ZANNOTATIONSELECTEDTEXT IS NOT NULL"
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["book_id"] = df["book_id"].astype(str).str.strip()
    df["highlight"] = df["highlight"].astype(str).str.strip()
    df["modified"] = pd.to_datetime(df["modified"], errors="coerce")

    for col in ["start_loc", "end_loc"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "chapter_name" in df.columns:
        df["chapter_name"] = df["chapter_name"].astype(str).str.strip()

    return df


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
    if "ZASSETLENGTH" in columns:
        select_cols.append("ZASSETLENGTH AS length")  # book length for page estimation

    query = f"SELECT {', '.join(select_cols)} FROM ZBKLIBRARYASSET WHERE ZASSETID IS NOT NULL"
    df = pd.read_sql_query(query, conn)
    conn.close()

    for col in ["title", "author"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    for col in ["date_added", "date_finished"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="s", errors="coerce")

    return df


def assign_chapters(df):
    """
    Assign chapters to annotations.
    Prefer `chapter_name`, else fallback to positions (start_loc).
    """
    if "chapter_name" in df.columns and df["chapter_name"].notnull().any():
        df["chapter"] = df["chapter_name"].fillna("Unknown")
    elif "start_loc" in df.columns:
        # Approximate chapters by splitting start_loc into groups
        df = df.sort_values(["book_id", "start_loc"])
        df["chapter"] = (df["start_loc"].diff().fillna(0) > 1000).cumsum().astype(str)
    else:
        df["chapter"] = "Unknown"
    return df


def deep_dive_book(book_id):
    annotations = load_annotations()
    books = load_books()

    book = books[books["book_id"] == book_id]
    if book.empty:
        print(f"Book {book_id} not found in library!")
        return

    annotations = annotations[annotations["book_id"] == book_id]
    if annotations.empty:
        print(f"No annotations found for book {book_id}")
        return

    annotations = assign_chapters(annotations)

    summary = annotations.groupby("chapter").agg(
        highlights_count=("highlight", "count"),
        colors_used=("color", lambda x: sorted(x.unique())),
        first_highlight=("modified", "min"),
        last_highlight=("modified", "max")
    ).reset_index()

    # Print chapters
    print(f"Book '{book.iloc[0]['title']}' has {len(summary)} chapters:")
    for i, row in summary.iterrows():
        print(f" - {row['chapter']} ({row['highlights_count']} highlights)")

    # Save JSON
    deep_dive = {
        "book_id": book_id,
        "title": book.iloc[0]["title"],
        "author": book.iloc[0]["author"],
        "date_added": book.iloc[0].get("date_added"),
        "date_finished": book.iloc[0].get("date_finished"),
        "chapters": summary.to_dict(orient="records")
    }
    out_path = SUMMARY_DIR / f"{book_id}_deep_dive.json"
    # Convert any int64 to int to avoid JSON issues
    for ch in deep_dive["chapters"]:
        for k, v in ch.items():
            if isinstance(v, (pd._libs.missing.NAType, pd.Timestamp)):
                ch[k] = str(v) if v is not pd.NaT else None
            elif isinstance(v, pd._libs.tslibs.nattype.NaTType):
                ch[k] = None
            elif isinstance(v, (pd.Int64Dtype, pd.int64, pd.int32)):
                ch[k] = int(v)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(deep_dive, f, indent=4, ensure_ascii=False)
    print(f"📄 Deep-dive saved to {out_path}")


if __name__ == "__main__":
    target_book_id = "1628E79AFBE404B6AD668AC7F1523921"  # replace with your book_id
    deep_dive_book(target_book_id)
