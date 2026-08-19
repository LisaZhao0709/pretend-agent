"""GDELT DOC 2.0 API client for collecting news/industry activity signals.

Uses a single timeline request per topic to minimize API calls and avoid
rate-limiting. The timeline response is split into monthly windows locally.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

GDELT_BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_TIMEOUT = 60
GDELT_RATE_LIMIT_SEC = 10.0
GDELT_MAX_RETRIES = 3
GDELT_RETRY_BACKOFF = 15.0

GDELT_HEADERS = {
    "User-Agent": "PredictiveAgents/0.1 (research project; mailto:research@example.com)",
}


def _cache_key(url: str, params: dict[str, Any]) -> str:
    raw = json.dumps({"url": url, "params": params}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


def _parse_gdelt_datetime(ym: str) -> str:
    """Convert YYYY-MM to GDELT datetime format YYYYMMDDHHMMSS."""
    return f"{ym.replace('-', '')}01000000"


def _extract_timeline(
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract daily data entries from GDELT timeline response.

    GDELT response structure:
        {"timeline": [{"series": "Article Count", "data": [{"date": ..., "value": ...}, ...]}]}

    Returns the list of {"date": ..., "value": ...} entries.
    """
    timeline = data.get("timeline", [])
    if not isinstance(timeline, list):
        return []
    for series in timeline:
        if isinstance(series, dict) and "data" in series:
            inner = series["data"]
            if isinstance(inner, list):
                return inner
    return []


def _parse_timeline_entry(entry: Any) -> tuple[str | None, int]:
    """Parse a timeline entry into (date_str, count).

    GDELT timeline entries can be dicts with 'date' and 'value' keys,
    or dicts with a single key like '20230101000000' mapping to a count.
    """
    if not isinstance(entry, dict):
        return None, 0

    if "date" in entry and "value" in entry:
        return entry["date"], int(entry["value"])

    for key, val in entry.items():
        if isinstance(val, (int, float)):
            return key, int(val)

    return None, 0


def fetch_gdelt_timeline(
    query: str,
    date_start: str,
    date_end: str,
    cache_dir: Path,
    timeout: int = GDELT_TIMEOUT,
    rate_limit: float = GDELT_RATE_LIMIT_SEC,
) -> dict[str, Any]:
    """Query GDELT DOC 2.0 API for full timeline in one request.

    Uses mode=timelinevolraw with timezoom=52 (weekly intervals) to get
    the entire date range in a single API call.

    Args:
        query: GDELT search query.
        date_start: Start in YYYY-MM format.
        date_end: End in YYYY-MM format.
        cache_dir: Directory for caching raw responses.
        timeout: Request timeout in seconds.
        rate_limit: Minimum seconds between requests.

    Returns:
        Dict with keys: timeline, url, params, fetched_at, cached.
    """
    params = {
        "query": query,
        "mode": "timelinevolraw",
        "startdatetime": _parse_gdelt_datetime(date_start),
        "enddatetime": _parse_gdelt_datetime(date_end),
        "timezoom": "52",
        "format": "json",
    }

    key = _cache_key(GDELT_BASE_URL, params)
    cpath = _cache_path(cache_dir, key)

    if cpath.exists():
        with open(cpath, "r", encoding="utf-8") as f:
            cached = json.load(f)
        timeline = _extract_timeline(cached["response"])
        return {
            "timeline": timeline,
            "url": cached["url"],
            "params": cached["params"],
            "fetched_at": cached["fetched_at"],
            "cached": True,
        }

    data = None
    for attempt in range(GDELT_MAX_RETRIES):
        time.sleep(rate_limit)
        resp = requests.get(
            GDELT_BASE_URL,
            params=params,
            headers=GDELT_HEADERS,
            timeout=timeout,
        )
        if resp.status_code == 429:
            wait = GDELT_RETRY_BACKOFF * (attempt + 1)
            print(f"      GDELT 429, retrying in {wait:.0f}s (attempt {attempt + 1}/{GDELT_MAX_RETRIES})...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        try:
            data = resp.json()
        except json.JSONDecodeError:
            data = {}
        break

    if data is None:
        data = {}

    fetched_at = datetime.utcnow().isoformat() + "Z"
    timeline = _extract_timeline(data)

    cache_record = {
        "url": GDELT_BASE_URL,
        "params": params,
        "fetched_at": fetched_at,
        "response": data,
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(cache_record, f, ensure_ascii=False, indent=2)

    return {
        "timeline": timeline,
        "url": GDELT_BASE_URL,
        "params": params,
        "fetched_at": fetched_at,
        "cached": False,
    }


def _gdelt_date_to_ym(date_str: str) -> str | None:
    """Convert GDELT datetime string to YYYY-MM.

    Handles formats like '20230101T000000Z' and '20230101000000'.
    """
    if not date_str or len(date_str) < 6:
        return None
    clean = date_str.split("T")[0] if "T" in date_str else date_str
    if len(clean) < 6:
        return None
    try:
        year = clean[:4]
        month = clean[4:6]
        int(year)
        int(month)
        return f"{year}-{month}"
    except (ValueError, IndexError):
        return None


def collect_gdelt_topic(
    topic_id: str,
    topic_label: str,
    query: str,
    windows: list[tuple[str, str]],
    cache_dir: Path,
) -> list[dict[str, Any]]:
    """Collect GDELT activity counts for a topic using a single timeline request.

    Makes one API call for the entire date range, then splits the timeline
    into monthly windows locally.

    Args:
        topic_id: Short identifier for the topic.
        topic_label: Human-readable topic name.
        query: GDELT search query.
        windows: List of (window_start, window_end) in YYYY-MM format.
        cache_dir: Cache directory for raw responses.

    Returns:
        List of activity records, one per window.
    """
    if not windows:
        return []

    overall_start = windows[0][0]
    overall_end = windows[-1][1]

    result = fetch_gdelt_timeline(
        query=query,
        date_start=overall_start,
        date_end=overall_end,
        cache_dir=cache_dir,
    )

    # Build monthly aggregation from timeline entries
    monthly_counts: dict[str, int] = {}
    for entry in result["timeline"]:
        date_str, count = _parse_timeline_entry(entry)
        if date_str:
            ym = _gdelt_date_to_ym(date_str)
            if ym:
                monthly_counts[ym] = monthly_counts.get(ym, 0) + count

    # Generate records for each requested window
    records: list[dict[str, Any]] = []
    for w_start, w_end in windows:
        count = monthly_counts.get(w_start, 0)
        records.append({
            "source": "gdelt",
            "topic_id": topic_id,
            "topic_label": topic_label,
            "window_start": w_start,
            "window_end": w_end,
            "activity_count": count,
            "collected_at": result["fetched_at"],
            "cached": result["cached"],
        })

    return records
