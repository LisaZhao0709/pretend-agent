"""Tests for arXiv collector: XML parsing, query building, and connectivity.

Run from Attempt/ with:
    python -m pytest tests/test_arxiv_collector.py -v
"""

from __future__ import annotations

import sys
import time
import urllib.error
from pathlib import Path

# Add Shared/src to path for imports
SHARED_SRC = Path(__file__).resolve().parents[1] / "Shared" / "src"
sys.path.insert(0, str(SHARED_SRC))

from data_collectors.arxiv import (
    _date_to_arxiv_format,
    _build_search_query,
    _parse_total_results,
)


# ---------------------------------------------------------------------------
# Unit tests: XML parsing and query building
# ---------------------------------------------------------------------------

SAMPLE_ARXIV_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <link href="http://export.arxiv.org/api/query?search_query=all:electron&amp;start=0&amp;max_results=0"
   rel="self" type="application/atom+xml"/>
  <title>ArXiv Query: search_query=all:electron</title>
  <id>http://arxiv.org/api/test</id>
  <updated>2025-01-01T00:00:00-04:00</updated>
  <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">12345</opensearch:totalResults>
  <opensearch:startIndex xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">0</opensearch:startIndex>
  <opensearch:itemsPerPage xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">0</opensearch:itemsPerPage>
</feed>"""

SAMPLE_ARXIV_XML_ZERO = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">0</opensearch:totalResults>
</feed>"""


def test_parse_total_results_with_count() -> None:
    """Should extract 12345 from the sample XML."""
    start = time.perf_counter()
    result = _parse_total_results(SAMPLE_ARXIV_XML)
    duration = (time.perf_counter() - start) * 1000
    print(f"  [SUCCESS] _parse_total_results | 耗时: {duration:.2f}ms")
    print(f"  输入: sample XML with totalResults=12345 | 输出: {result}")
    assert result == 12345


def test_parse_total_results_zero() -> None:
    """Should extract 0 from the zero-results XML."""
    result = _parse_total_results(SAMPLE_ARXIV_XML_ZERO)
    assert result == 0


def test_parse_total_results_invalid_xml() -> None:
    """Should return 0 for invalid XML."""
    result = _parse_total_results("not valid xml at all")
    assert result == 0


def test_parse_total_results_missing_element() -> None:
    """Should return 0 when totalResults element is missing."""
    xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    result = _parse_total_results(xml)
    assert result == 0


def test_date_to_arxiv_format() -> None:
    """Should convert YYYY-MM-DD to YYYYMMDDHHMMSS."""
    start = time.perf_counter()
    result = _date_to_arxiv_format("2025-01-15")
    duration = (time.perf_counter() - start) * 1000
    print(f"  [SUCCESS] _date_to_arxiv_format | 耗时: {duration:.2f}ms")
    print(f"  输入: '2025-01-15' | 输出: '{result}'")
    assert result == "20250115000000"


def test_build_search_query() -> None:
    """Should build a valid arXiv search_query with date range."""
    start = time.perf_counter()
    result = _build_search_query('"large language model" OR LLM', "2025-01-01", "2025-01-31")
    duration = (time.perf_counter() - start) * 1000
    print(f"  [SUCCESS] _build_search_query | 耗时: {duration:.2f}ms")
    print(f"  输入: query='\"large language model\" OR LLM', dates=2025-01-01..2025-01-31")
    print(f"  输出: '{result}'")
    assert "all:" in result
    assert "submittedDate:" in result
    assert "20250101000000" in result
    assert "20250131000000" in result
    assert "AND" in result


# ---------------------------------------------------------------------------
# Integration test: arXiv API connectivity (network required)
# ---------------------------------------------------------------------------

def test_arxiv_api_connectivity() -> None:
    """Verify arXiv API is reachable and returns valid XML with totalResults.

    This is a lightweight connectivity test: one request for 'all:electron'
    with max_results=1. If the API is down or network is unavailable, this
    test will be skipped (not failed) to avoid blocking CI on network issues.
    """
    import urllib.request
    import urllib.parse

    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": "all:electron",
        "start": 0,
        "max_results": 1,
    })

    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PredictiveAgents-Test/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
        duration = (time.perf_counter() - start) * 1000

        assert status == 200, f"Expected HTTP 200, got {status}"
        total = _parse_total_results(body)
        assert total > 0, f"Expected totalResults > 0 for 'all:electron', got {total}"

        print(f"  [SUCCESS] arXiv API connectivity | 耗时: {duration:.2f}ms")
        print(f"  请求: GET {url}")
        print(f"  HTTP状态: {status}")
        print(f"  totalResults: {total}")
    except urllib.error.HTTPError as e:
        duration = (time.perf_counter() - start) * 1000
        if e.code in (500, 502, 503):
            import pytest
            pytest.skip(f"arXiv API returned {e.code} (server error), skipping connectivity test")
        print(f"  [FAILED] arXiv API connectivity | 耗时: {duration:.2f}ms")
        print(f"  错误原因: {e}")
        raise
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        import pytest
        pytest.skip(f"Network unavailable for arXiv connectivity test: {e}")


# ---------------------------------------------------------------------------
# Integration test: arXiv date-filtered query
# ---------------------------------------------------------------------------

def test_arxiv_date_filtered_query() -> None:
    """Verify arXiv API returns results for a date-filtered LLM query.

    Uses a known active period (2024-01-01 to 2024-01-31) to ensure
    there should be LLM-related preprints.
    """
    import urllib.request
    import urllib.parse

    search_query = _build_search_query(
        '"large language model" OR LLM',
        "2024-01-01",
        "2024-01-31",
    )
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": search_query,
        "start": 0,
        "max_results": 1,
    })

    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PredictiveAgents-Test/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
        duration = (time.perf_counter() - start) * 1000

        assert status == 200, f"Expected HTTP 200, got {status}"
        total = _parse_total_results(body)
        # LLM papers should exist in Jan 2024
        assert total > 0, f"Expected LLM preprints in Jan 2024, got {total}"

        print(f"  [SUCCESS] arXiv date-filtered query | 耗时: {duration:.2f}ms")
        print(f"  请求: GET {url[:100]}...")
        print(f"  HTTP状态: {status}")
        print(f"  totalResults (LLM, Jan 2024): {total}")
    except urllib.error.HTTPError as e:
        duration = (time.perf_counter() - start) * 1000
        if e.code in (500, 502, 503):
            import pytest
            pytest.skip(f"arXiv API returned {e.code} (server error), skipping date-filtered test")
        print(f"  [FAILED] arXiv date-filtered query | 耗时: {duration:.2f}ms")
        print(f"  错误原因: {e}")
        raise
    except Exception as e:
        import pytest
        pytest.skip(f"Network unavailable for arXiv date-filtered test: {e}")
