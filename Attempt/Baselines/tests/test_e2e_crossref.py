"""End-to-end validation: CrossRef collect -> normalize -> pivot -> quality check.

Uses the new unified collector API (CrossrefCollector via registry).

Run: python -m Baselines.tests.test_e2e_crossref
"""
from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ATTEMPT_ROOT = Path(__file__).resolve().parents[2]
SHARED_SRC = ATTEMPT_ROOT / "Shared" / "src"
sys.path.insert(0, str(SHARED_SRC))

import data_collectors.crossref  # noqa: F401 - registers collector
from data_collectors.base import get_collector
from processors.normalize import (
    create_pivot_table,
    merge_records_by_source,
    save_records_to_jsonl,
)
from processors.quality_checker import check_data_quality


@dataclass
class _TopicStub:
    topic_id: str
    topic_label: str
    openalex_query: str
    gdelt_query: str
    crossref_query: str


@dataclass
class _CfgStub:
    topics: list[Any]
    raw_api_path: Path
    interim_path: Path
    start_date: str
    end_date: str


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        topic = _TopicStub(
            topic_id="large_language_models",
            topic_label="Large Language Models",
            openalex_query='"large language model" OR LLM',
            gdelt_query="large language model",
            crossref_query='"large language model" OR LLM',
        )
        cfg = _CfgStub(
            topics=[topic],
            raw_api_path=tmp / "raw",
            interim_path=tmp / "interim",
            start_date="2023-01",
            end_date="2023-04",
        )
        http_settings = {"min_interval_seconds": 0.1, "max_retries": 2, "timeout_seconds": 30}
        source_cfg = {"mailto": "research@example.com"}

        print("=== Phase 1: Collect CrossRef data (1 topic, 3 months) ===")
        collector = get_collector("crossref")
        records = collector.collect(cfg, http_settings, source_cfg)
        print(f"Collected {len(records)} records:")
        for r in records:
            print(f"  {r['window_start']}: count={r['activity_count']} status={r['collection_status']} cached={r['cached']}")

        interim_dir = tmp / "interim"
        interim_dir.mkdir(parents=True, exist_ok=True)
        cr_path = interim_dir / "crossref_activity.jsonl"
        save_records_to_jsonl(records, cr_path)
        print(f"Saved: {cr_path}")

        print()
        print("=== Phase 2: Normalize and pivot ===")
        gdelt_records = [
            {
                "source": "gdelt",
                "topic_id": "large_language_models",
                "topic_label": "Large Language Models",
                "window_start": w["window_start"],
                "window_end": w["window_end"],
                "activity_count": 1000 + i * 100,
                "collection_status": "ok",
            }
            for i, w in enumerate(records)
        ]
        merged = merge_records_by_source([], gdelt_records, records)
        pivot = create_pivot_table(merged)
        print(f"Pivot table ({len(pivot)} rows):")
        for row in pivot:
            print(
                f"  {row['window_start']}: crossref={row['crossref_count']}, "
                f"gdelt={row['gdelt_count']}, openalex={row['openalex_count']}"
            )

        print()
        print("=== Phase 3: Quality check ===")
        quality = check_data_quality(pivot)
        print(f"Overall score: {quality['overall_score']}")
        print(f"Issues: {quality['issues']}")
        for tid, t in quality["by_topic"].items():
            print(
                f"  {tid}: crossref_cov={t['crossref_coverage']:.2f}, "
                f"gdelt_cov={t['gdelt_coverage']:.2f}"
            )

    print()
    print("=== End-to-end validation passed ===")


if __name__ == "__main__":
    main()
