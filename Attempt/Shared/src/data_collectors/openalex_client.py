"""OpenAlex Works API client for collecting academic activity signals.

Uses group_by=publication_date to fetch all daily counts in a single
request per topic, then aggregates to monthly windows locally.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

OPENALEX_BASE_URL = "https://api.openalex.org/works"
OPENALEX_TIMEOUT = 60
OPENALEX_RATE_LIMIT_SEC = 3.0
OPENALEX_MAX_RETRIES = 5
OPENALEX_RETRY_BACKOFF = 30.0


def _cache_key(url: str, params: dict[str, Any]) -> str:
    raw = json.dumps({"url": url, "params": params}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


def fetch_openalex_grouped(
    query: str,
    date_start: str,
    date_end: str,
    cache_dir: Path,
    email: str = "research@example.com",
    timeout: int = OPENALEX_TIMEOUT,
    rate_limit: float = OPENALEX_RATE_LIMIT_SEC,
) -> dict[str, Any]:
    """Query OpenAlex Works API with group_by to get daily counts in one request.

    Args:
        query: Search query string.
        date_start: Start date YYYY-MM-DD.
        date_end: End date YYYY-MM-DD.
        cache_dir: Directory for caching raw responses.
        email: Email for OpenAlex polite pool.
        timeout: Request timeout in seconds.
        rate_limit: Minimum seconds between requests.

    Returns:
        Dict with keys: groups, url, params, fetched_at, cached.
    """
    params = {
        "search": query,
        "filter": f"from_publication_date:{date_start},to_publication_date:{date_end}",
        "group_by": "publication_date",
        "per_page": 500,
        "mailto": email,
    }

    key = _cache_key(OPENALEX_BASE_URL, params)
    cpath = _cache_path(cache_dir, key)

    if cpath.exists():
        with open(cpath, "r", encoding="utf-8") as f:
            cached = json.load(f)
        groups = cached["response"].get("group_by", [])
        return {
            "groups": groups,
            "url": cached["url"],
            "params": cached["params"],
            "fetched_at": cached["fetched_at"],
            "cached": True,
        }

    data = None
    for attempt in range(OPENALEX_MAX_RETRIES):
        time.sleep(rate_limit)
        resp = requests.get(OPENALEX_BASE_URL, params=params, timeout=timeout)
        if resp.status_code == 429:
            wait = OPENALEX_RETRY_BACKOFF * (attempt + 1)
            print(f"      OpenAlex 429, retrying in {wait:.0f}s (attempt {attempt + 1}/{OPENALEX_MAX_RETRIES})...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        break

    if data is None:
        raise RuntimeError(f"OpenAlex API rate-limited after {OPENALEX_MAX_RETRIES} retries")

    fetched_at = datetime.utcnow().isoformat() + "Z"

    cache_record = {
        "url": OPENALEX_BASE_URL,
        "params": params,
        "fetched_at": fetched_at,
        "response": data,
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(cache_record, f, ensure_ascii=False, indent=2)

    groups = data.get("group_by", [])
    return {
        "groups": groups,
        "url": OPENALEX_BASE_URL,
        "params": params,
        "fetched_at": fetched_at,
        "cached": False,
    }


def _date_to_ym(date_str: str) -> str | None:
    """Convert YYYY-MM-DD to YYYY-MM."""
    if not date_str or len(date_str) < 7:
        return None
    return date_str[:7]


def collect_openalex_topic(
    topic_id: str,
    topic_label: str,
    query: str,
    windows: list[tuple[str, str]],
    cache_dir: Path,
    email: str = "research@example.com",
) -> list[dict[str, Any]]:
    """Collect OpenAlex activity counts for a topic using a single group_by request.

    Makes one API call for the entire date range with group_by=publication_date,
    then aggregates daily counts into monthly windows.

    Args:
        topic_id: Short identifier for the topic.
        topic_label: Human-readable topic name.
        query: OpenAlex search query.
        windows: List of (window_start, window_end) in YYYY-MM format.
        cache_dir: Cache directory for raw responses.
        email: Email for OpenAlex polite pool.

    Returns:
        List of activity records, one per window.
    """
    if not windows:
        return []

    overall_start = f"{windows[0][0]}-01"
    overall_end = f"{windows[-1][1]}-01"

    result = fetch_openalex_grouped(
        query=query,
        date_start=overall_start,
        date_end=overall_end,
        cache_dir=cache_dir,
        email=email,
    )

    # Build monthly aggregation from group_by results
    # group_by entries look like: {"key": "2023-01-15", "count": 42}
    monthly_counts: dict[str, int] = {}
    for group in result["groups"]:
        date_str = group.get("key", "")
        count = group.get("count", 0)
        ym = _date_to_ym(date_str)
        if ym:
            monthly_counts[ym] = monthly_counts.get(ym, 0) + count

    # Generate records for each requested window
    records: list[dict[str, Any]] = []
    for w_start, w_end in windows:
        count = monthly_counts.get(w_start, 0)
        records.append({
            "source": "openalex",
            "topic_id": topic_id,
            "topic_label": topic_label,
            "window_start": w_start,
            "window_end": w_end,
            "activity_count": count,
            "collected_at": result["fetched_at"],
            "cached": result["cached"],
        })

    return records
