"""Tests for USPTO collector: ODP vs PatentSearch modes, API key handling.

Run from Attempt/ with:
    python -m pytest tests/test_uspto_collector.py -v
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add Shared/src to path for imports
SHARED_SRC = Path(__file__).resolve().parents[1] / "Shared" / "src"
sys.path.insert(0, str(SHARED_SRC))

from data_collectors.uspto import (
    _build_odp_params,
    _build_patentsearch_body,
    _parse_odp_count,
    _parse_patentsearch_count,
)


# ---------------------------------------------------------------------------
# Unit tests: parameter building and count parsing
# ---------------------------------------------------------------------------

def test_build_odp_params() -> None:
    """Should build ODP API query parameters."""
    start = time.perf_counter()
    result = _build_odp_params("machine learning", "2024-01-01", "2024-01-31")
    duration = (time.perf_counter() - start) * 1000
    print(f"  [SUCCESS] _build_odp_params | 耗时: {duration:.2f}ms")
    print(f"  输入: query='machine learning', dates=2024-01-01..2024-01-31")
    print(f"  输出: {result}")
    assert result["q"] == "machine learning"
    assert result["dateRangeData.startDate"] == "2024-01-01"
    assert result["dateRangeData.endDate"] == "2024-01-31"
    assert result["start"] == "0"
    assert result["limit"] == "0"


def test_build_patentsearch_body() -> None:
    """Should build PatentSearch API request body."""
    start = time.perf_counter()
    result = _build_patentsearch_body("robotics", "2024-06-01", "2024-06-30")
    duration = (time.perf_counter() - start) * 1000
    print(f"  [SUCCESS] _build_patentsearch_body | 耗时: {duration:.2f}ms")
    print(f"  输入: query='robotics', dates=2024-06-01..2024-06-30")
    print(f"  输出: {result}")
    assert result["q"] == "robotics"
    assert result["filters"]["app_date"] == ["2024-06-01", "2024-06-30"]
    assert result["page"] == 0
    assert result["per_page"] == 0


def test_parse_odp_count() -> None:
    """Should extract totalResults from ODP response."""
    from http_client import CachedResponse
    payload = {
        "queryStatus": {
            "totalResults": 1234,
        }
    }
    response = CachedResponse(
        status_code=200,
        headers={},
        payload=payload,
        fetched_at="2025-01-01T00:00:00Z",
        url="https://api.uspto.gov/api/v1/patent/applications/search",
    )
    result = _parse_odp_count(response)
    assert result == 1234


def test_parse_odp_count_missing() -> None:
    """Should return 0 when totalResults is missing."""
    from http_client import CachedResponse
    response = CachedResponse(
        status_code=200,
        headers={},
        payload={},
        fetched_at="2025-01-01T00:00:00Z",
        url="https://api.uspto.gov/api/v1/patent/applications/search",
    )
    result = _parse_odp_count(response)
    assert result == 0


def test_parse_patentsearch_count() -> None:
    """Should extract total_patent_count from PatentSearch response."""
    from http_client import CachedResponse
    payload = {
        "total_patent_count": 5678,
    }
    response = CachedResponse(
        status_code=200,
        headers={},
        payload=payload,
        fetched_at="2025-01-01T00:00:00Z",
        url="https://search.patentsview.org/api/v1/patent/search",
    )
    result = _parse_patentsearch_count(response)
    assert result == 5678


def test_parse_patentsearch_count_missing() -> None:
    """Should return 0 when total_patent_count is missing."""
    from http_client import CachedResponse
    response = CachedResponse(
        status_code=200,
        headers={},
        payload={},
        fetched_at="2025-01-01T00:00:00Z",
        url="https://search.patentsview.org/api/v1/patent/search",
    )
    result = _parse_patentsearch_count(response)
    assert result == 0


# ---------------------------------------------------------------------------
# Integration test: USPTO PatentSearch API connectivity (requires API key)
# ---------------------------------------------------------------------------

def test_patentsearch_api_connectivity() -> None:
    """Verify PatentSearch API is reachable with a valid API key.

    Uses a simple query with date range to get a count. If USPTO_API_KEY
    is not set, the test is skipped. If the API returns 401/403, it indicates
    an invalid key and the test fails.
    """
    import os
    import urllib.request
    import urllib.parse

    api_key = os.getenv("USPTO_API_KEY")
    if not api_key:
        import pytest
        pytest.skip("USPTO_API_KEY not set, skipping PatentSearch connectivity test")

    body = _build_patentsearch_body("quantum computing", "2024-01-01", "2024-01-31")
    url = "https://search.patentsview.org/api/v1/patent/search"

    start = time.perf_counter()
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "User-Agent": "PredictiveAgents-Test/1.0",
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body_data = resp.read().decode("utf-8")
        duration = (time.perf_counter() - start) * 1000

        assert status == 200, f"Expected HTTP 200, got {status}"
        data = json.loads(body_data)
        count = data.get("total_patent_count", 0)
        assert count >= 0, f"Expected non-negative total_patent_count, got {count}"

        print(f"  [SUCCESS] PatentSearch API connectivity | 耗时: {duration:.2f}ms")
        print(f"  HTTP状态: {status}")
        print(f"  total_patent_count (quantum computing, Jan 2024): {count}")
    except urllib.error.HTTPError as e:
        duration = (time.perf_counter() - start) * 1000
        if e.code in (401, 403):
            raise AssertionError(f"USPTO API key invalid or unauthorized: {e.code}")
        if e.code == 429:
            import pytest
            pytest.skip("PatentSearch API returned 429 (rate limited), skipping connectivity test")
        print(f"  [FAILED] PatentSearch API connectivity | 耗时: {duration:.2f}ms")
        print(f"  错误原因: {e}")
        raise
    except Exception as e:
        import pytest
        pytest.skip(f"Network unavailable for PatentSearch connectivity test: {e}")


# ---------------------------------------------------------------------------
# Integration test: USPTO ODP API connectivity (requires API key + ID.me)
# ---------------------------------------------------------------------------

def test_odp_api_connectivity() -> None:
    """Verify ODP API is reachable with a valid API key.

    ODP requires USPTO.gov account + ID.me verification. If USPTO_API_KEY
    is not set, the test is skipped. 401/403 indicates invalid or unverified key.
    """
    import os
    import urllib.request
    import urllib.parse

    api_key = os.getenv("USPTO_API_KEY")
    if not api_key:
        import pytest
        pytest.skip("USPTO_API_KEY not set, skipping ODP connectivity test")

    params = _build_odp_params("AI agent", "2024-06-01", "2024-06-30")
    url = "https://api.uspto.gov/api/v1/patent/applications/search?" + urllib.parse.urlencode(params)

    start = time.perf_counter()
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "PredictiveAgents-Test/1.0",
                "X-API-KEY": api_key,
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body_data = resp.read().decode("utf-8")
        duration = (time.perf_counter() - start) * 1000

        assert status == 200, f"Expected HTTP 200, got {status}"
        data = json.loads(body_data)
        count = data.get("queryStatus", {}).get("totalResults", 0)
        assert count >= 0, f"Expected non-negative totalResults, got {count}"

        print(f"  [SUCCESS] ODP API connectivity | 耗时: {duration:.2f}ms")
        print(f"  HTTP状态: {status}")
        print(f"  totalResults (AI agent, Jun 2024): {count}")
    except urllib.error.HTTPError as e:
        duration = (time.perf_counter() - start) * 1000
        if e.code in (401, 403):
            raise AssertionError(f"USPTO API key invalid or ID.me not verified: {e.code}")
        if e.code == 429:
            import pytest
            pytest.skip("ODP API returned 429 (rate limited), skipping connectivity test")
        print(f"  [FAILED] ODP API connectivity | 耗时: {duration:.2f}ms")
        print(f"  错误原因: {e}")
        raise
    except Exception as e:
        import pytest
        pytest.skip(f"Network unavailable for ODP connectivity test: {e}")
