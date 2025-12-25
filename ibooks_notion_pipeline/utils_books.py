import re
from difflib import SequenceMatcher


# -----------------------------
# Title normalization (identity)
# -----------------------------
def normalize_title(title: str) -> str:
    """
    Canonical title normalization used for ALL matching
    (DB ↔ JSON ↔ Notion).
    """
    if not title:
        return ""

    title = title.lower()
    title = re.sub(r"\(.*?\)", "", title)        # remove ISBN / parentheses
    title = re.sub(r"[:–—\-]", " ", title)       # normalize separators
    title = re.sub(r"[^\w\s]", "", title)        # remove punctuation
    title = re.sub(r"\s+", " ", title).strip()   # collapse whitespace

    return title


# -----------------------------
# Filesystem-safe filenames
# -----------------------------
def make_safe_filename(title: str) -> str:
    """
    Deterministic, readable, filesystem-safe filename.
    """
    name = title.replace(":", "_")
    name = re.sub(r"[^\w\s\-_]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return f"{name}.json"


# -----------------------------
# Fuzzy similarity
# -----------------------------
def similarity(a: str, b: str) -> float:
    """
    Returns similarity score between 0 and 1.
    """
    return SequenceMatcher(None, a, b).ratio()


FOCUS_BOOK_TITLES = [
    "Hedge Fund Market Wizards",
    "Quantitative Trading",
    "Alpha Trader",
    "The Mental Game of Trading: A System for Solving Problems With Greed, Fear, Anger, Confidence, and Discipline",
    "The little Book of Trading",
    "The Little Book of Common Sense Investing: The Only Way to Guarantee Your Fair Share of Stock Market Returns",
    "Principles for Dealing With the Changing World Order : Why Nations Succeed and Fail (9781982164799)",
    "The Psychology of Money: Timeless Lessons on Wealth, Greed, and Happiness",
    "The Mental Strategies of Top Traders",
    "Stock Market Wizards",
    "The Front Office",
    "Inside the House of Money",
    "Souverän Investieren mit Indexfonds & ETFs",
    "Quantitative Trading"
]