"""Data normalization processor: convert collected records to standardized JSONL."""

from __future__ import annotations

import json
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
) -> list[dict[str, Any]]:
    """Merge OpenAlex and GDELT records into a single sorted list.

    Records are sorted by topic_id, then window_start, then source.

    Args:
        openalex_records: Activity records from OpenAlex.
        gdelt_records: Activity records from GDELT.

    Returns:
        Merged and sorted list of all records.
    """
    merged = openalex_records + gdelt_records
    merged.sort(key=lambda r: (r["topic_id"], r["window_start"], r["source"]))
    return merged


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
    """Pivot records so each row has one window with both openalex and gdelt counts.

    Args:
        records: Merged activity records.

    Returns:
        List of dicts with keys: topic_id, topic_label, window_start,
        openalex_count, gdelt_count.
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
                "gdelt_count": 0,
            }
        if rec["source"] == "openalex":
            pivot[key]["openalex_count"] = rec["activity_count"]
        elif rec["source"] == "gdelt":
            pivot[key]["gdelt_count"] = rec["activity_count"]

    result = list(pivot.values())
    result.sort(key=lambda r: (r["topic_id"], r["window_start"]))
    return result
