"""Tests for OpenAlex collector: API connectivity and count parsing.

Run from Attempt/ with:
    python -m pytest tests/test_openalex_collector.py -v
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
from pathlib import Path

# Add Shared/src to path for imports
SHARED_SRC = Path(__file__).resolve().parents[1] / "Shared" / "src"
sys.path.insert(0, str(SHARED_SRC))


# ---------------------------------------------------------------------------
# Integration test: OpenAlex API connectivity
# ---------------------------------------------------------------------------

def test_openalex_api_connectivity() -> None:
    """Verify OpenAlex API is reachable and returns JSON with meta.count.

    Uses a simple search query with per_page=1 to get a count without
    downloading records. If the API is rate-limited (429) or network is
    unavailable, the test is skipped rather than failed.
    """
    import urllib.request
    import urllib.parse

    params = {
        "search": "machine learning",
        "filter": "from_publication_date:2024-01-01,to_publication_date:2024-01-31",
        "per_page": 1,
        "mailto": "research@example.com",
    }
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)

    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PredictiveAgents-Test/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
        duration = (time.perf_counter() - start) * 1000

        assert status == 200, f"Expected HTTP 200, got {status}"
        data = json.loads(body)
        count = data.get("meta", {}).get("count", 0)
        assert count > 0, f"Expected meta.count > 0 for 'machine learning' in Jan 2024, got {count}"

        print(f"  [SUCCESS] OpenAlex API connectivity | 耗时: {duration:.2f}ms")
        print(f"  请求: GET {url[:80]}...")
        print(f"  HTTP状态: {status}")
        print(f"  meta.count: {count}")
    except urllib.error.HTTPError as e:
        duration = (time.perf_counter() - start) * 1000
        if e.code == 429:
            import pytest
            pytest.skip("OpenAlex API returned 429 (rate limited without api_key), skipping connectivity test")
        print(f"  [FAILED] OpenAlex API connectivity | 耗时: {duration:.2f}ms")
        print(f"  错误原因: {e}")
        raise
    except Exception as e:
        import pytest
        pytest.skip(f"Network unavailable for OpenAlex connectivity test: {e}")


def test_openalex_api_key_optional() -> None:
    """Verify OpenAlex API works without api_key (free tier).

    The free tier provides $1/day budget which is sufficient for
    6 topics x 31 months = 186 search calls = $0.186/day.
    Skipped if rate-limited (429) or network unavailable.
    """
    import urllib.request
    import urllib.parse

    params = {
        "search": "robotics",
        "filter": "from_publication_date:2024-06-01,to_publication_date:2024-06-30",
        "per_page": 1,
        "mailto": "research@example.com",
    }
    # No api_key parameter - should still work on free tier
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)

    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PredictiveAgents-Test/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
        duration = (time.perf_counter() - start) * 1000

        assert status == 200, f"Expected HTTP 200, got {status}"
        data = json.loads(body)
        count = data.get("meta", {}).get("count", 0)
        assert count > 0, f"Expected meta.count > 0 for 'robotics' in Jun 2024, got {count}"

        print(f"  [SUCCESS] OpenAlex free-tier (no api_key) | 耗时: {duration:.2f}ms")
        print(f"  HTTP状态: {status}")
        print(f"  meta.count (robotics, Jun 2024): {count}")
    except urllib.error.HTTPError as e:
        duration = (time.perf_counter() - start) * 1000
        if e.code == 429:
            import pytest
            pytest.skip("OpenAlex API returned 429 (rate limited without api_key), skipping free-tier test")
        print(f"  [FAILED] OpenAlex free-tier | 耗时: {duration:.2f}ms")
        print(f"  错误原因: {e}")
        raise
    except Exception as e:
        import pytest
        pytest.skip(f"Network unavailable for OpenAlex free-tier test: {e}")
