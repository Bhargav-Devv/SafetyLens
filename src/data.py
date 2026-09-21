"""
Loading and preparing the OSHA Severe Injury Reports.

Two label granularities are produced deliberately:

  fine   - the raw OIICS EventTitle (363 categories, ~76 usable)
  major  - the OIICS major event group (7 categories)

Reporting only the coarse task would overstate the system; reporting only the
fine task would understate it. Both are trained and both are reported.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg


def _read(path: Path) -> tuple[pd.DataFrame | None, str | None]:
    """Try each encoding in turn. Returns (dataframe, encoding used)."""
    for enc in cfg.ENCODINGS:
        try:
            if path.suffix.lower() == ".xlsx":
                return pd.read_excel(path), "xlsx"
            return pd.read_csv(path, low_memory=False, encoding=enc), enc
        except UnicodeDecodeError:
            continue
        except Exception:
            continue
    return None, None


def _is_osha(df: pd.DataFrame) -> bool:
    """Guard against silently training on the wrong CSV."""
    cols = " ".join(str(c).lower() for c in df.columns)
    return "narrative" in cols and "event" in cols


def find_raw_file() -> Path:
    """Largest validated CSV/XLSX, searched across a few sensible locations.

    Looks in data/raw first, then the project folder and its parent, so the CSV
    works from wherever you downloaded it - no moving files around.
    """
    cfg.DATA_RAW.mkdir(parents=True, exist_ok=True)

    search_dirs = [cfg.DATA_RAW, cfg.ROOT, cfg.ROOT.parent,
                   Path.home() / "Downloads"]

    candidates = []
    for directory in search_dirs:
        try:
            candidates += [p for p in directory.glob("*")
                           if p.suffix.lower() in (".csv", ".xlsx") and p.is_file()]
        except OSError:
            continue

    candidates.sort(key=lambda p: -p.stat().st_size)
    if not candidates:
        raise FileNotFoundError(
            "No CSV or XLSX found. Searched:\n  "
            + "\n  ".join(str(d) for d in search_dirs)
            + "\n\nPut the OSHA Severe Injury Reports CSV in data/raw/."
        )
    return candidates[0]


def load_raw() -> pd.DataFrame:
    path = find_raw_file()
    df, enc = _read(path)
    if df is None:
        raise ValueError(f"Could not decode {path.name} with any of {cfg.ENCODINGS}")
    if not _is_osha(df):
        raise ValueError(f"{path.name} does not look like OSHA data (columns: {list(df.columns)[:8]})")
    print(f"loaded {path.name}  encoding={enc}  rows={len(df):,}")
    return df


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Narrative + both label granularities. One row per usable incident."""
    d = df[[cfg.TEXT_COL, cfg.FINE_COL, cfg.CODE_COL]].dropna().copy()
    d.columns = ["text", "fine", "code"]

    d["text"] = d["text"].astype(str).str.strip()
    d = d[d["text"].str.len() > cfg.MIN_NARRATIVE_CHARS]

    d["code"] = pd.to_numeric(d["code"], errors="coerce")
    d = d.dropna(subset=["code"])

    # The OIICS major group is the FIRST DIGIT AS WRITTEN. Codes are variable
    # length (e.g. 64, 531, 1214), so zero-padding to four digits is wrong - it
    # turns 531 (exposure) into 0531 and reads the group as 0. That bug filed
    # 2,192 heat-exposure incidents under "Nonclassifiable".
    d["major"] = d["code"].astype(int).astype(str).str[0].map(cfg.MAJOR_GROUPS)
    d = d.dropna(subset=["major"]).reset_index(drop=True)

    if cfg.COLLAPSE_ROADWAY:
        d["fine"] = _collapse_roadway(d["fine"])

    print(f"usable incidents : {len(d):,}")
    print(f"fine classes     : {d['fine'].nunique()}")
    print(f"major groups     : {d['major'].nunique()}")
    return d


def _collapse_roadway(fine: pd.Series) -> pd.Series:
    """Fold the 28 public-roadway OIICS events into one class.

    The substring test has to exclude "nonroadway", which contains "roadway"
    and means the opposite - a forklift in a warehouse aisle, which 1910.178
    governs, versus a car on a highway, which nothing in 1910 governs.

    Splitting one real-world category across 28 labels of 63, 49, 47, 43, 31 and
    a tail below 20 is not granularity anyone benefits from: every one of them
    was dropped by the rare-class filter, so the classifier was trained to be
    unable to say "this happened on a public road" at all.
    """
    is_road = (fine.str.contains("roadway", case=False, na=False)
               & ~fine.str.contains("nonroadway", case=False, na=False))
    n_labels = fine[is_road].nunique()
    n_rows = int(is_road.sum())
    out = fine.copy()
    out[is_road] = cfg.ROADWAY_CLASS
    print(f"roadway collapse : {n_labels} labels -> 1 class, {n_rows:,} records")
    return out


def filter_rare(d: pd.DataFrame, target: str) -> pd.DataFrame:
    """Drop classes too small to evaluate. Below ~150 examples the per-class
    metrics are noise and reporting them would be dishonest."""
    counts = d[target].value_counts()
    keep = counts[counts >= cfg.MIN_EXAMPLES_PER_CLASS].index
    out = d[d[target].isin(keep)]
    print(f"  {target}: kept {len(keep)} classes, {len(out):,} of {len(d):,} records")
    return out
