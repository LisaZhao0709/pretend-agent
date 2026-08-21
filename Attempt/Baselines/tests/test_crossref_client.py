"""Test CrossRef collector: count fetching, monthly aggregation, cache hit, and failure handling.

Uses the new unified collector API (CrossrefCollector class via registry).

Run: python -m Baselines.tests.test_crossref_client
"""
from __future__ import annotations

import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Ensure Shared/src is importable
ATTEMPT_ROOT = Path(__file__).resolve().parents[2]
SHARED_SRC = ATTEMPT_ROOT / "Shared" / "src"
sys.path.insert(0, str(SHARED_SRC))

import data_collectors.crossref  # noqa: F401 - registers collector
from data_collectors.base import get_collector, registered_sources
from data_collectors.crossref import CrossrefCollector
from config import month_range
from http_client import PoliteApiClient, CachedResponse


def run_test(func, *args, **kwargs):
    start = time.perf_counter()
    try:
        res = func(*args, **kwargs)
        duration = (time.perf_counter() - start) * 1000
        print(f" [SUCCESS] 函数: {func.__name__} | 耗时: {duration:.2f}ms")
        print(f" 输入: {args} {kwargs}")
        print(f" 输出: {res if not isinstance(res, list) else f'<list of {len(res)} items>'}")
        return res
    except Exception as e:
        print(f" [FAILED] 函数: {func.__name__} | 错误原因: {e}")
        raise


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


def _make_cfg(tmp: Path, topics: list[Any], start: str = "2023-01", end: str = "2023-03") -> _CfgStub:
    return _CfgStub(
        topics=topics,
        raw_api_path=tmp / "raw",
        interim_path=tmp / "interim",
        start_date=start,
        end_date=end,
    )


def test_month_range():
    """Test month_range converts YYYY-MM to (first_day, last_day)."""
    print("\n=== test_month_range ===")
    run_test(month_range, "2023-01")
    run_test(month_range, "2023-02")
    run_test(month_range, "2023-12")
    run_test(month_range, "2024-02")  # leap year
    assert month_range("2023-01") == ("2023-01-01", "2023-01-31")
    assert month_range("2023-02") == ("2023-02-01", "2023-02-28")
    assert month_range("2023-12") == ("2023-12-01", "2023-12-31")
    assert month_range("2024-02") == ("2024-02-01", "2024-02-29")
    print("  All assertions passed.")


def test_registry():
    """Test that crossref is registered and get_collector returns it."""
    print("\n=== test_registry ===")
    sources = run_test(registered_sources)
    assert "crossref" in sources, f"crossref not registered: {sources}"
    collector = run_test(get_collector, "crossref")
    assert collector.source_name == "crossref"
    print("  Registry OK.")


def test_collector_live():
    """Live test: CrossrefCollector.collect against real API (1 topic, 2 months)."""
    print("\n=== test_collector_live (live API) ===")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        topic = _TopicStub(
            topic_id="large_language_models",
            topic_label="Large Language Models",
            openalex_query='"large language model" OR LLM',
            gdelt_query="large language model",
            crossref_query='"large language model" OR LLM',
        )
        cfg = _make_cfg(tmp, [topic], start="2023-01", end="2023-03")
        http_settings = {"min_interval_seconds": 0.1, "max_retries": 2, "timeout_seconds": 30}
        source_cfg = {"mailto": "research@example.com"}

        collector = get_collector("crossref")
        records = run_test(collector.collect, cfg, http_settings, source_cfg)

        assert len(records) == 2, f"Expected 2 records (2 months), got {len(records)}"
        for rec in records:
            assert rec["source"] == "crossref"
            assert rec["topic_id"] == "large_language_models"
            assert rec["collection_status"] == "ok", f"unexpected status: {rec}"
            assert rec["activity_count"] > 0, f"Expected non-zero count, got {rec['activity_count']}"
            assert "window_start" in rec and "window_end" in rec
            assert "collected_at" in rec and "cached" in rec
        print(f"  All {len(records)} records valid (live).")

        # Second call should hit cache
        print("\n  Second call (should hit cache):")
        records2 = run_test(collector.collect, cfg, http_settings, source_cfg)
        assert len(records2) == 2
        assert all(r["cached"] for r in records2), "Expected all cached=True on second call"
        print("  Cache hit verified.")


def test_collector_failure_handling():
    """Test that a bad endpoint produces failed records, not a crash."""
    print("\n=== test_collector_failure_handling ===")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        topic = _TopicStub(
            topic_id="test_topic",
            topic_label="Test",
            openalex_query="test",
            gdelt_query="test",
            crossref_query="test",
        )
        cfg = _make_cfg(tmp, [topic], start="2023-01", end="2023-02")
        # Point to a non-existent host to trigger request failures fast
        http_settings = {
            "min_interval_seconds": 0.1,
            "max_retries": 1,
            "timeout_seconds": 2,
        }
        # Patch the class attribute to force a connection error
        from data_collectors.crossref import CrossrefCollector
        original = CrossrefCollector.base_url
        CrossrefCollector.base_url = "https://nonexistent.invalid.example/works"
        try:
            collector = get_collector("crossref")
            records = run_test(collector.collect, cfg, http_settings, {"mailto": "x@example.com"})
        finally:
            CrossrefCollector.base_url = original

        assert len(records) == 1, f"Expected 1 failed record, got {len(records)}"
        rec = records[0]
        assert rec["collection_status"] == "failed", f"Expected failed, got {rec['collection_status']}"
        assert rec["activity_count"] is None
        assert "error" in rec
        print(f"  Failure handled gracefully: error='{rec['error'][:60]}...'")


def main():
    test_month_range()
    test_registry()
    with tempfile.TemporaryDirectory():
        test_collector_live()
    test_collector_failure_handling()
    print("\n=== All CrossRef collector tests passed ===")


if __name__ == "__main__":
    main()
