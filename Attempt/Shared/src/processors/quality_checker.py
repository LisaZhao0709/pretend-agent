"""Data quality checker: validates collected records and emits quality_report.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def check_data_quality(
    pivot_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assess data completeness and quality.

    Returns a report dict with:
    - overall_score (0-100)
    - by_topic: topic-level coverage and signal counts
    - issues: list of detected problems
    """
    report = {
        "overall_score": 100,
        "by_topic": {},
        "issues": [],
    }

    if not pivot_records:
        report["overall_score"] = 0
        report["issues"].append("No records found")
        return report

    # Group by topic
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for rec in pivot_records:
        tid = rec.get("topic_id", "unknown")
        if tid not in by_topic:
            by_topic[tid] = []
        by_topic[tid].append(rec)

    # Analyze per-topic
    for tid, recs in by_topic.items():
        topic_label = recs[0].get("topic_label", tid) if recs else tid
        openalex_count = sum(1 for r in recs if r.get("openalex_count", 0) > 0)
        crossref_count = sum(1 for r in recs if r.get("crossref_count", 0) > 0)
        gdelt_count = sum(1 for r in recs if r.get("gdelt_count", 0) > 0)
        github_count = sum(1 for r in recs if r.get("github_stars_total", 0) > 0)

        coverage = (openalex_count + crossref_count + gdelt_count + github_count) / (len(recs) * 4) if recs else 0
        report["by_topic"][tid] = {
            "label": topic_label,
            "windows": len(recs),
            "openalex_coverage": openalex_count / len(recs) if recs else 0,
            "crossref_coverage": crossref_count / len(recs) if recs else 0,
            "gdelt_coverage": gdelt_count / len(recs) if recs else 0,
            "github_coverage": github_count / len(recs) if recs else 0,
            "overall_coverage": coverage,
        }

        if coverage < 0.3:
            report["issues"].append(f"Topic {tid}: low coverage ({coverage:.1%})")
        if openalex_count == 0 and crossref_count == 0:
            report["issues"].append(f"Topic {tid}: no academic data (OpenAlex and CrossRef both empty)")
        if gdelt_count == 0:
            report["issues"].append(f"Topic {tid}: no GDELT data")

    # Overall score
    avg_coverage = sum(t["overall_coverage"] for t in report["by_topic"].values()) / len(report["by_topic"]) if report["by_topic"] else 0
    report["overall_score"] = int(avg_coverage * 100)

    return report


def save_quality_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
