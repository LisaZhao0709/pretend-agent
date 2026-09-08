"""Data normalization processor: convert collected records to standardized JSONL.

Provides:
- JSONL I/O utilities (save_records_to_jsonl, load_jsonl)
- Record merging and pivot table construction
- Cross-source standardization methods (robust scaling, rank-based normalization)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def save_records_to_jsonl(
    records: list[dict[str, Any]],
    output_path: Path,
) -> int:
    """Save activity records to a JSONL file.

    Args:
        records: List of activity record dicts.
        output_path: Path to output .jsonl file.

    Returns:
        Number of records written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load records from a JSONL file.

    Args:
        path: Path to .jsonl file.

    Returns:
        List of record dicts.
    """
    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def merge_records_by_source(
    openalex_records: list[dict[str, Any]],
    gdelt_records: list[dict[str, Any]],
    crossref_records: list[dict[str, Any]] | None = None,
    github_records: list[dict[str, Any]] | None = None,
    arxiv_records: list[dict[str, Any]] | None = None,
    uspto_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Merge OpenAlex, CrossRef, arXiv, USPTO, GDELT and GitHub records into a single sorted list.

    Records are sorted by topic_id, then window_start, then source.

    Args:
        openalex_records: Activity records from OpenAlex.
        gdelt_records: Activity records from GDELT.
        crossref_records: Activity records from CrossRef (optional, may be empty).
        github_records: Activity records from GitHub (optional, may be empty).
        arxiv_records: Activity records from arXiv (optional, may be empty).
        uspto_records: Activity records from USPTO (optional, may be empty).

    Returns:
        Merged and sorted list of all records.
    """
    if crossref_records is None:
        crossref_records = []
    if github_records is None:
        github_records = []
    if arxiv_records is None:
        arxiv_records = []
    if uspto_records is None:
        uspto_records = []
    merged = openalex_records + crossref_records + arxiv_records + uspto_records + gdelt_records + github_records
    merged.sort(key=lambda r: (r["topic_id"], r["window_start"], r["source"]))
    return merged


def _safe_count(value: Any) -> int:
    """Coerce an activity_count value to int, treating None/failed as 0.

    New-schema records carry ``activity_count: None`` when
    ``collection_status == "failed"``. The pivot table needs numeric counts so
    downstream quality checks and models do not trip on None comparisons.
    """
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_feature_matrix(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group records by topic_id for downstream model consumption.

    Args:
        records: Merged activity records from all sources.

    Returns:
        Dict mapping topic_id to list of records sorted by window_start.
    """
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        tid = rec["topic_id"]
        if tid not in by_topic:
            by_topic[tid] = []
        by_topic[tid].append(rec)

    for tid in by_topic:
        by_topic[tid].sort(key=lambda r: (r["window_start"], r["source"]))

    return by_topic


def create_pivot_table(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Pivot records so each row has one window with per-source counts.

    Args:
        records: Merged activity records.

    Returns:
        List of dicts with keys: topic_id, topic_label, window_start,
        openalex_count, crossref_count, arxiv_count, uspto_count, gdelt_count, github_count.
    """
    pivot: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in records:
        key = (rec["topic_id"], rec["window_start"])
        if key not in pivot:
            pivot[key] = {
                "topic_id": rec["topic_id"],
                "topic_label": rec["topic_label"],
                "window_start": rec["window_start"],
                "openalex_count": 0,
                "crossref_count": 0,
                "arxiv_count": 0,
                "uspto_count": 0,
                "gdelt_count": 0,
                "github_count": 0,
            }
        if rec["source"] == "openalex":
            pivot[key]["openalex_count"] = _safe_count(rec.get("activity_count"))
        elif rec["source"] == "crossref":
            pivot[key]["crossref_count"] = _safe_count(rec.get("activity_count"))
        elif rec["source"] == "arxiv":
            pivot[key]["arxiv_count"] = _safe_count(rec.get("activity_count"))
        elif rec["source"] == "uspto":
            pivot[key]["uspto_count"] = _safe_count(rec.get("activity_count"))
        elif rec["source"] == "gdelt":
            pivot[key]["gdelt_count"] = _safe_count(rec.get("activity_count"))
        elif rec["source"] == "github":
            pivot[key]["github_count"] = _safe_count(rec.get("activity_count"))

    result = list(pivot.values())
    result.sort(key=lambda r: (r["topic_id"], r["window_start"]))
    return result


# ---------------------------------------------------------------------------
# Cross-source standardization methods
# ---------------------------------------------------------------------------

def robust_scale(values: list[float]) -> list[float]:
    """Robust scaling using median and IQR (resistant to outliers).

    scaled = (value - median) / IQR

    If IQR is zero (all values identical or degenerate), returns zeros.

    Args:
        values: List of numeric values.

    Returns:
        Scaled values with median=0, IQR=1.
    """
    n = len(values)
    if n == 0:
        return []
    sorted_vals = sorted(values)
    median = sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    q1 = sorted_vals[n // 4] if n >= 4 else sorted_vals[0]
    q3 = sorted_vals[3 * n // 4] if n >= 4 else sorted_vals[-1]
    iqr = q3 - q1
    if iqr < 1e-9:
        return [0.0] * n
    return [(v - median) / iqr for v in values]


def rank_normalize(values: list[float]) -> list[float]:
    """Rank-based normalization to [0, 1] range.

    Maps each value to its rank fraction: rank / (n - 1).
    Ties get the average rank. This is completely immune to outlier magnitude.

    Args:
        values: List of numeric values.

    Returns:
        Values in [0, 1] where 0 = smallest, 1 = largest.
    """
    n = len(values)
    if n <= 1:
        return [0.5] * n
    indexed = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and values[indexed[j + 1]] == values[indexed[i]]:
            j += 1
        avg_rank = (i + j) / 2
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg_rank / (n - 1)
        i = j + 1
    return ranks


def log1p_normalize(values: list[float]) -> list[float]:
    """Log1p transform followed by min-max normalization to [0, 1].

    Compresses large values while keeping zero at zero.
    If all values are zero or identical, returns 0.5 for all.

    Args:
        values: List of numeric values.

    Returns:
        Normalized values in [0, 1].
    """
    n = len(values)
    if n == 0:
        return []
    log_vals = [math.log1p(max(v, 0.0)) for v in values]
    lo, hi = min(log_vals), max(log_vals)
    if hi - lo < 1e-9:
        return [0.5] * n
    return [(v - lo) / (hi - lo) for v in log_vals]


def standardize_pivot(
    pivot: list[dict[str, Any]],
    source_columns: list[str] | None = None,
    method: str = "robust",
) -> list[dict[str, Any]]:
    """Add standardized columns to pivot table for each source.

    Adds ``{col}_std`` columns using the specified method. Original columns
    are preserved. Standardization is done per-source across all topics and
    windows (global), so that cross-topic comparisons are meaningful.

    Args:
        pivot: Pivot table rows.
        source_columns: Columns to standardize (default: all *_count).
        method: One of "robust" (median+IQR), "rank" (rank-based [0,1]),
            "log1p" (log1p + min-max), "minmax" (plain min-max).

    Returns:
        Pivot with added ``{col}_std`` columns.
    """
    if source_columns is None:
        source_columns = [
            c for c in (pivot[0].keys() if pivot else [])
            if c.endswith("_count")
        ]

    for col in source_columns:
        values = [float(row.get(col, 0)) for row in pivot]
        if method == "robust":
            scaled = robust_scale(values)
        elif method == "rank":
            scaled = rank_normalize(values)
        elif method == "log1p":
            scaled = log1p_normalize(values)
        elif method == "minmax":
            n = len(values)
            if n == 0:
                scaled = []
            else:
                lo, hi = min(values), max(values)
                if hi - lo < 1e-9:
                    scaled = [0.5] * n
                else:
                    scaled = [(v - lo) / (hi - lo) for v in values]
        else:
            raise ValueError(f"Unknown standardization method: {method!r}")
        for i, row in enumerate(pivot):
            row[f"{col}_std"] = round(scaled[i], 4)

    return pivot
