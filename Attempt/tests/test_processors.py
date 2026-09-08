"""Tests for processors: detector, cleaner, normalize standardization.

Run from Attempt/ with:
    python -m pytest tests/test_processors.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add Shared/src to path for imports
SHARED_SRC = Path(__file__).resolve().parents[1] / "Shared" / "src"
sys.path.insert(0, str(SHARED_SRC))

from processors.detector import (
    detect_zscore_outliers,
    detect_iqr_outliers,
    detect_consecutive_zeros,
    detect_sudden_drop,
    tag_anomalies_in_pivot,
    summarize_anomalies,
)
from processors.cleaner import (
    filter_failed_records,
    filter_anomalous_pivot_rows,
    fill_missing_windows,
    smooth_signal,
    clean_records,
)
from processors.normalize import (
    robust_scale,
    rank_normalize,
    log1p_normalize,
    standardize_pivot,
)


# ---------------------------------------------------------------------------
# Detector tests
# ---------------------------------------------------------------------------

def test_zscore_outlier_detection() -> None:
    """A single extreme spike should be flagged; normal values should not."""
    values = [10, 12, 11, 10, 13, 500, 11, 10]
    outliers = detect_zscore_outliers(values, threshold=2.5)
    assert outliers[5] is True  # the 500 spike
    assert sum(outliers) == 1


def test_zscore_no_outliers_in_constant_series() -> None:
    values = [5, 5, 5, 5, 5]
    outliers = detect_zscore_outliers(values)
    assert not any(outliers)


def test_iqr_outlier_detection() -> None:
    values = [1, 2, 3, 4, 5, 6, 7, 8, 100]
    outliers = detect_iqr_outliers(values, k=1.5)
    assert outliers[-1] is True  # 100 is an outlier
    assert not outliers[0]


def test_consecutive_zeros_flagged() -> None:
    values = [10, 0, 0, 0, 10, 0, 10]
    tags = detect_consecutive_zeros(values, min_consecutive=3)
    assert tags[1] == "likely_api_failure"
    assert tags[2] == "likely_api_failure"
    assert tags[3] == "likely_api_failure"
    assert tags[5] == ""  # single zero, not flagged
    assert tags[0] == ""


def test_sudden_drop_detected() -> None:
    values = [10, 20, 30, 40, 0, 10]
    tags = detect_sudden_drop(values, min_nonzero_before=3)
    assert tags[4] == "sudden_drop"
    assert tags[0] == ""


def test_tag_anomalies_in_pivot() -> None:
    pivot = [
        {"topic_id": "ai", "topic_label": "AI", "window_start": "2026-01", "crossref_count": 10, "gdelt_count": 100},
        {"topic_id": "ai", "topic_label": "AI", "window_start": "2026-02", "crossref_count": 12, "gdelt_count": 110},
        {"topic_id": "ai", "topic_label": "AI", "window_start": "2026-03", "crossref_count": 11, "gdelt_count": 105},
        {"topic_id": "ai", "topic_label": "AI", "window_start": "2026-04", "crossref_count": 5000, "gdelt_count": 120},
        {"topic_id": "ai", "topic_label": "AI", "window_start": "2026-05", "crossref_count": 10, "gdelt_count": 130},
    ]
    tagged = tag_anomalies_in_pivot(pivot, zscore_threshold=1.5)
    assert "crossref_count_zscore_outlier" in tagged[0]
    assert tagged[3]["crossref_count_zscore_outlier"] is True  # 5000 is an outlier
    summary = summarize_anomalies(tagged)
    assert summary["total_anomalies"] > 0


# ---------------------------------------------------------------------------
# Cleaner tests
# ---------------------------------------------------------------------------

def test_filter_failed_records() -> None:
    records = [
        {"source": "crossref", "topic_id": "ai", "window_start": "2026-01", "activity_count": 10, "collection_status": "ok"},
        {"source": "crossref", "topic_id": "ai", "window_start": "2026-02", "activity_count": None, "collection_status": "failed"},
        {"source": "gdelt", "topic_id": "ai", "window_start": "2026-01", "activity_count": 100, "collection_status": "ok"},
    ]
    ok, failed = filter_failed_records(records)
    assert len(ok) == 2
    assert len(failed) == 1
    assert failed[0]["collection_status"] == "failed"


def test_clean_records_log() -> None:
    records = [
        {"source": "crossref", "topic_id": "ai", "activity_count": 10, "collection_status": "ok"},
        {"source": "crossref", "topic_id": "ai", "activity_count": None, "collection_status": "failed"},
        {"source": "gdelt", "topic_id": "ai", "activity_count": 100, "collection_status": "ok"},
    ]
    clean, log = clean_records(records)
    assert len(clean) == 2
    assert log["input_count"] == 3
    assert log["ok_count"] == 2
    assert log["failed_count"] == 1
    assert log["failed_by_source"]["crossref"] == 1


def test_filter_anomalous_pivot_rows() -> None:
    pivot = [
        {"topic_id": "ai", "window_start": "2026-01", "crossref_count": 10, "gdelt_count": 100,
         "crossref_count_any_anomaly": False, "gdelt_count_any_anomaly": False,
         "crossref_count_zero_tag": "", "gdelt_count_zero_tag": ""},
        {"topic_id": "ai", "window_start": "2026-02", "crossref_count": 0, "gdelt_count": 0,
         "crossref_count_any_anomaly": True, "gdelt_count_any_anomaly": True,
         "crossref_count_zero_tag": "likely_api_failure", "gdelt_count_zero_tag": "likely_api_failure"},
        {"topic_id": "ai", "window_start": "2026-03", "crossref_count": 15, "gdelt_count": 0,
         "crossref_count_any_anomaly": False, "gdelt_count_any_anomaly": True,
         "crossref_count_zero_tag": "", "gdelt_count_zero_tag": "likely_api_failure"},
    ]
    cleaned, counts = filter_anomalous_pivot_rows(pivot, drop_likely_api_failure=True)
    # Row 2 (both sources API failure) should be dropped
    # Row 3 (only gdelt failure) should be kept
    assert len(cleaned) == 2
    assert counts["likely_api_failure"] == 1
    assert cleaned[1]["window_start"] == "2026-03"


def test_fill_missing_windows() -> None:
    pivot = [
        {"topic_id": "ai", "topic_label": "AI", "window_start": "2026-01", "crossref_count": 10, "gdelt_count": 100},
        {"topic_id": "ai", "topic_label": "AI", "window_start": "2026-03", "crossref_count": 20, "gdelt_count": 200},
    ]
    all_windows = ["2026-01", "2026-02", "2026-03"]
    filled, counts = fill_missing_windows(pivot, all_windows, strategy="forward_fill")
    assert len(filled) == 3
    assert counts["filled"] == 1
    assert filled[1]["window_start"] == "2026-02"
    assert filled[1]["_filled"] is True
    assert filled[1]["crossref_count"] == 10  # forward-filled from 2026-01


def test_smooth_signal_median() -> None:
    pivot = [
        {"topic_id": "ai", "window_start": "2026-01", "crossref_count": 10},
        {"topic_id": "ai", "window_start": "2026-02", "crossref_count": 100},  # spike
        {"topic_id": "ai", "window_start": "2026-03", "crossref_count": 12},
    ]
    smoothed = smooth_signal(pivot, window_size=3, method="median")
    assert "crossref_count_smoothed" in smoothed[0]
    # Median of [10, 100, 12] = 12, so the spike at index 1 should be smoothed down
    assert smoothed[1]["crossref_count_smoothed"] == 12
    assert smoothed[0]["crossref_count_smoothed"] < 100  # edge effect


# ---------------------------------------------------------------------------
# Normalize standardization tests
# ---------------------------------------------------------------------------

def test_robust_scale() -> None:
    values = [1, 2, 3, 4, 5, 6, 7, 8, 100]  # 100 is an outlier
    scaled = robust_scale(values)
    median = sorted(values)[len(values) // 2]
    # The outlier should have a very high scaled value
    assert scaled[-1] > scaled[0]
    # Median should map to approximately 0
    median_idx = values.index(median)
    assert abs(scaled[median_idx]) < 0.01


def test_rank_normalize() -> None:
    values = [10, 20, 30, 40, 50]
    ranked = rank_normalize(values)
    assert ranked[0] == 0.0  # smallest
    assert ranked[-1] == 1.0  # largest
    assert all(0 <= r <= 1 for r in ranked)


def test_rank_normalize_ties() -> None:
    values = [10, 20, 20, 30]
    ranked = rank_normalize(values)
    # Ties at index 1,2 should get the same rank
    assert ranked[1] == ranked[2]


def test_log1p_normalize() -> None:
    values = [0, 10, 100, 1000]
    normalized = log1p_normalize(values)
    assert normalized[0] == 0.0  # log1p(0) = 0, min
    assert normalized[-1] == 1.0  # log1p(1000) = max
    assert all(0 <= v <= 1 for v in normalized)


def test_standardize_pivot_robust() -> None:
    pivot = [
        {"topic_id": "ai", "window_start": "2026-01", "crossref_count": 10, "gdelt_count": 100},
        {"topic_id": "ai", "window_start": "2026-02", "crossref_count": 15, "gdelt_count": 200},
        {"topic_id": "ai", "window_start": "2026-03", "crossref_count": 12, "gdelt_count": 150},
    ]
    result = standardize_pivot(pivot, method="robust")
    assert "crossref_count_std" in result[0]
    assert "gdelt_count_std" in result[0]


def test_standardize_pivot_rank() -> None:
    pivot = [
        {"topic_id": "ai", "window_start": "2026-01", "crossref_count": 10},
        {"topic_id": "ai", "window_start": "2026-02", "crossref_count": 20},
        {"topic_id": "ai", "window_start": "2026-03", "crossref_count": 30},
    ]
    result = standardize_pivot(pivot, method="rank")
    assert result[0]["crossref_count_std"] == 0.0
    assert result[-1]["crossref_count_std"] == 1.0
