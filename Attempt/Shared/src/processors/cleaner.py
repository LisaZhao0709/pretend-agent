"""Data cleaning rules for collected activity records.

Cleans both raw records (before pivot) and pivot rows (after pivot):
- Filter out failed collections (collection_status != "ok")
- Filter out records with None activity_count
- Mark and optionally remove consecutive-zero runs (likely API failures)
- Fill missing windows with configurable strategy (zero_fill, forward_fill, interpolate)
- Smooth signal with optional moving median (more robust than moving average)

All cleaning steps are configurable and produce a cleaning log so the
transformation from raw to clean data is fully traceable.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def filter_failed_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split records into (ok, failed) based on collection_status.

    Args:
        records: Raw activity records from collectors.

    Returns:
        Tuple of (ok_records, failed_records).
    """
    ok: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for rec in records:
        if rec.get("collection_status", "ok") != "ok" or rec.get("activity_count") is None:
            failed.append(rec)
        else:
            ok.append(rec)
    return ok, failed


def filter_anomalous_pivot_rows(
    pivot: list[dict[str, Any]],
    source_columns: list[str] | None = None,
    drop_zscore: bool = False,
    drop_iqr: bool = False,
    drop_likely_api_failure: bool = True,
    drop_sudden_drop: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Filter pivot rows based on anomaly tags from detector.tag_anomalies_in_pivot.

    A row is dropped only if ALL source columns have the specified anomaly type.
    This avoids dropping an entire month just because one source had an outlier.

    Args:
        pivot: Pivot table with anomaly tags.
        source_columns: Columns to check (default: all *_count columns).
        drop_zscore: Drop rows where all sources have zscore outlier.
        drop_iqr: Drop rows where all sources have iqr outlier.
        drop_likely_api_failure: Drop rows where all sources tagged likely_api_failure.
        drop_sudden_drop: Drop rows where all sources tagged sudden_drop.

    Returns:
        Tuple of (cleaned_pivot, drop_counts).
    """
    if source_columns is None:
        source_columns = [
            c for c in (pivot[0].keys() if pivot else [])
            if c.endswith("_count")
        ]

    drop_counts = {
        "zscore": 0,
        "iqr": 0,
        "likely_api_failure": 0,
        "sudden_drop": 0,
        "total_dropped": 0,
    }

    cleaned: list[dict[str, Any]] = []
    for row in pivot:
        drop = False
        if drop_zscore and all(row.get(f"{c}_zscore_outlier", False) for c in source_columns):
            drop = True
            drop_counts["zscore"] += 1
        if drop_iqr and all(row.get(f"{c}_iqr_outlier", False) for c in source_columns):
            drop = True
            drop_counts["iqr"] += 1
        if drop_likely_api_failure and all(
            row.get(f"{c}_zero_tag", "") == "likely_api_failure" for c in source_columns
        ):
            drop = True
            drop_counts["likely_api_failure"] += 1
        if drop_sudden_drop and all(
            row.get(f"{c}_zero_tag", "") == "sudden_drop" for c in source_columns
        ):
            drop = True
            drop_counts["sudden_drop"] += 1

        if drop:
            drop_counts["total_dropped"] += 1
        else:
            cleaned.append(row)

    return cleaned, drop_counts


def fill_missing_windows(
    pivot: list[dict[str, Any]],
    all_windows: list[str],
    source_columns: list[str] | None = None,
    strategy: str = "zero_fill",
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Fill missing time windows for each topic with a configurable strategy.

    Args:
        pivot: Pivot table (sorted by topic_id, window_start).
        all_windows: Complete list of expected window_start values (YYYY-MM).
        source_columns: Count columns to fill (default: all *_count).
        strategy: One of "zero_fill", "forward_fill", "interpolate".

    Returns:
        Tuple of (filled_pivot, fill_counts).
    """
    if source_columns is None:
        source_columns = [
            c for c in (pivot[0].keys() if pivot else [])
            if c.endswith("_count")
        ]

    if not all_windows:
        return pivot, {"filled": 0}

    # Group existing rows by topic_id
    by_topic: dict[str, dict[str, dict[str, Any]]] = {}
    topic_labels: dict[str, str] = {}
    for row in pivot:
        tid = row.get("topic_id", "unknown")
        ws = row.get("window_start", "")
        by_topic.setdefault(tid, {})[ws] = row
        topic_labels[tid] = row.get("topic_label", tid)

    fill_counts = {"filled": 0, "by_strategy": {strategy: 0}}

    result: list[dict[str, Any]] = []
    for tid in sorted(by_topic.keys()):
        topic_label = topic_labels.get(tid, tid)
        prev_values: dict[str, float] = {}
        for ws in all_windows:
            existing = by_topic.get(tid, {}).get(ws)
            if existing is not None:
                # Update prev_values for interpolation/forward_fill
                for col in source_columns:
                    prev_values[col] = float(existing.get(col, 0))
                result.append(existing)
            else:
                # Create a filled row
                new_row: dict[str, Any] = {
                    "topic_id": tid,
                    "topic_label": topic_label,
                    "window_start": ws,
                    "_filled": True,
                }
                for col in source_columns:
                    if strategy == "zero_fill":
                        new_row[col] = 0
                    elif strategy == "forward_fill":
                        new_row[col] = prev_values.get(col, 0)
                    elif strategy == "interpolate":
                        # Simple linear interpolation: use prev value (no future lookahead)
                        new_row[col] = prev_values.get(col, 0)
                    else:
                        new_row[col] = 0
                # Copy non-count columns from the nearest existing row if available
                nearest = next(
                    (by_topic[tid][w] for w in all_windows if w in by_topic.get(tid, {})),
                    None,
                )
                if nearest:
                    for key, val in nearest.items():
                        if key not in new_row and not key.endswith("_count"):
                            new_row[key] = val
                result.append(new_row)
                fill_counts["filled"] += 1
                fill_counts["by_strategy"][strategy] = fill_counts["by_strategy"].get(strategy, 0) + 1

    result.sort(key=lambda r: (r["topic_id"], r["window_start"]))
    return result, fill_counts


def smooth_signal(
    pivot: list[dict[str, Any]],
    source_columns: list[str] | None = None,
    window_size: int = 3,
    method: str = "median",
) -> list[dict[str, Any]]:
    """Apply moving median or moving average smoothing to source columns.

    Adds ``{col}_smoothed`` columns alongside the original ``{col}`` columns.
    The original values are preserved; smoothing is additive.

    Args:
        pivot: Pivot table (sorted by topic_id, window_start).
        source_columns: Columns to smooth (default: all *_count).
        window_size: Rolling window size (default 3).
        method: "median" or "mean".

    Returns:
        Pivot with added ``{col}_smoothed`` columns.
    """
    if source_columns is None:
        source_columns = [
            c for c in (pivot[0].keys() if pivot else [])
            if c.endswith("_count")
        ]

    by_topic: dict[str, list[dict[str, Any]]] = {}
    for row in pivot:
        tid = row.get("topic_id", "unknown")
        by_topic.setdefault(tid, []).append(row)

    for tid, rows in by_topic.items():
        for col in source_columns:
            values = [float(row.get(col, 0)) for row in rows]
            smoothed = _rolling_smooth(values, window_size, method)
            for i, row in enumerate(rows):
                row[f"{col}_smoothed"] = round(smoothed[i], 2)

    return pivot


def _rolling_smooth(
    values: list[float],
    window_size: int,
    method: str,
) -> list[float]:
    """Apply rolling smoothing to a list of values.

    Args:
        values: Input time series.
        window_size: Rolling window size.
        method: "median" or "mean".

    Returns:
        Smoothed series of the same length.
    """
    n = len(values)
    if n == 0:
        return []
    half = window_size // 2
    result: list[float] = []
    for i in range(n):
        start = max(0, i - half)
        end = min(n, i + half + 1)
        window = values[start:end]
        if method == "median":
            window_sorted = sorted(window)
            mid = len(window_sorted) // 2
            if len(window_sorted) % 2 == 0:
                result.append((window_sorted[mid - 1] + window_sorted[mid]) / 2)
            else:
                result.append(window_sorted[mid])
        else:
            result.append(sum(window) / len(window) if window else 0.0)
    return result


def clean_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Full cleaning pipeline for raw activity records (before pivot).

    Steps:
    1. Filter out failed collections and None activity_count.

    Args:
        records: Raw activity records from collectors.

    Returns:
        Tuple of (clean_records, cleaning_log).
    """
    ok, failed = filter_failed_records(records)
    log = {
        "input_count": len(records),
        "ok_count": len(ok),
        "failed_count": len(failed),
        "failed_by_source": {},
    }
    for rec in failed:
        src = rec.get("source", "unknown")
        log["failed_by_source"][src] = log["failed_by_source"].get(src, 0) + 1
    return ok, log


def save_cleaning_log(log: dict[str, Any], path: Path) -> None:
    """Save cleaning log to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
