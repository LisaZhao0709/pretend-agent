"""OpenAlex, CrossRef and GDELT collection adapters."""

from __future__ import annotations

import os
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .config import ForecastConfig
from .http_client import PoliteApiClient

LOGGER = logging.getLogger(__name__)


def date_windows(end_date: date, count: int, window_days: int) -> list[tuple[date, date]]:
    """Return consecutive historical windows ending immediately before end_date."""

    windows: list[tuple[date, date]] = []
    window_end = end_date - timedelta(days=1)
    for _ in range(count):
        window_start = window_end - timedelta(days=window_days - 1)
        windows.append((window_start, window_end))
        window_end = window_start - timedelta(days=1)
    return list(reversed(windows))


def collect_openalex(config: ForecastConfig, as_of: date) -> list[dict[str, Any]]:
    """Collect one count per topic and historical window from OpenAlex."""

    api = config.raw["openalex"]
    cache_dir = config.paths["raw_api_dir"] / "openalex"
    client = PoliteApiClient(cache_dir, config.http)
    key_name = api.get("api_key_env", "OPENALEX_API_KEY")
    api_key = os.getenv(key_name)
    results: list[dict[str, Any]] = []
    windows = date_windows(as_of, int(config.raw["history_windows"]), int(config.raw["window_days"]))

    for topic_id, topic in config.raw["openalex"]["topics"].items():
        for start, end in windows:
            params: dict[str, Any] = {
                "search": topic["query"],
                "filter": f"from_publication_date:{start.isoformat()},to_publication_date:{end.isoformat()}",
                "per_page": int(api.get("per_page", 1)),
                "select": "id,publication_date",
            }
            if api_key:
                params["api_key"] = api_key
            try:
                response = client.get_json(api["base_url"], params, cache_key=f"openalex_{topic_id}_{start}_{end}")
            except Exception as exc:  # noqa: BLE001 - preserve partial collection progress
                LOGGER.warning("OpenAlex request failed for %s %s..%s: %s", topic_id, start, end, exc)
                results.append(
                    {
                        "source": "openalex",
                        "topic_id": topic_id,
                        "topic_label": topic["label"],
                        "window_start": start.isoformat(),
                        "window_end": end.isoformat(),
                        "activity_count": None,
                        "collection_status": "failed",
                        "error": str(exc),
                    }
                )
                continue
            results.append(
                {
                    "source": "openalex",
                    "topic_id": topic_id,
                    "topic_label": topic["label"],
                    "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                    "activity_count": int(response.payload.get("meta", {}).get("count", 0)),
                    "collected_at": response.fetched_at,
                }
            )
    return results


def collect_gdelt(config: ForecastConfig, as_of: date) -> list[dict[str, Any]]:
    """Collect article counts from GDELT timelinevolraw over short windows."""

    api = config.raw["gdelt"]
    cache_dir = config.paths["raw_api_dir"] / "gdelt"
    client = PoliteApiClient(cache_dir, config.http)
    results: list[dict[str, Any]] = []
    windows = date_windows(as_of, int(config.raw["history_windows"]), int(config.raw["window_days"]))

    for topic_id, topic in config.raw["gdelt"]["topics"].items():
        for start, end in windows:
            params = {
                "query": topic["query"],
                "mode": api["mode"],
                "format": api["format"],
                "startdatetime": start.strftime("%Y%m%d000000"),
                "enddatetime": end.strftime("%Y%m%d235959"),
            }
            try:
                response = client.get_json(api["base_url"], params, cache_key=f"gdelt_{topic_id}_{start}_{end}")
            except Exception as exc:  # noqa: BLE001 - collection must preserve partial progress
                LOGGER.warning("GDELT request failed for %s %s..%s: %s", topic_id, start, end, exc)
                results.append(
                    {
                        "source": "gdelt",
                        "topic_id": topic_id,
                        "topic_label": topic["label"],
                        "window_start": start.isoformat(),
                        "window_end": end.isoformat(),
                        "activity_count": None,
                        "collection_status": "failed",
                        "error": str(exc),
                    }
                )
                continue
            # Detect non-JSON responses (GDELT sometimes returns plain-text errors)
            if "_non_json_body" in response.payload:
                LOGGER.warning("GDELT returned non-JSON response for %s %s..%s: %s", topic_id, start, end, response.payload["_non_json_body"][:100])
                results.append(
                    {
                        "source": "gdelt",
                        "topic_id": topic_id,
                        "topic_label": topic["label"],
                        "window_start": start.isoformat(),
                        "window_end": end.isoformat(),
                        "activity_count": None,
                        "collection_status": "failed",
                        "error": f"non-JSON response: {response.payload['_non_json_body'][:100]}",
                    }
                )
                continue
            timeline = response.payload.get("timeline") or response.payload.get("data") or []
            activity_count = sum(_timeline_value(point) for point in timeline)
            results.append(
                {
                    "source": "gdelt",
                    "topic_id": topic_id,
                    "topic_label": topic["label"],
                    "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                    "activity_count": activity_count,
                    "collection_status": "ok",
                    "collected_at": response.fetched_at,
                }
            )
    return results


def _timeline_value(point: dict[str, Any]) -> int:
    """Read the raw count field across GDELT response variants."""

    for key in ("value", "count", "articles"):
        if key in point:
            return int(float(point[key]))
    return 0


def collect_crossref(config: ForecastConfig, as_of: date) -> list[dict[str, Any]]:
    """Collect publication counts from CrossRef Works API over short windows.

    Uses rows=1 so message.total-results gives the count directly.
    Replaces OpenAlex which suffers from group_by emptiness and credits paywall.
    """

    api = config.raw["crossref"]
    cache_dir = config.paths["raw_api_dir"] / "crossref"
    client = PoliteApiClient(cache_dir, config.http)
    mailto_env = api.get("mailto_env", "CROSSREF_MAILTO")
    mailto = os.getenv(mailto_env, api.get("mailto_default", "research@example.com"))
    results: list[dict[str, Any]] = []
    windows = date_windows(as_of, int(config.raw["history_windows"]), int(config.raw["window_days"]))

    for topic_id, topic in config.raw["crossref"]["topics"].items():
        for start, end in windows:
            params: dict[str, Any] = {
                "query": topic["query"],
                "filter": f"from-pub-date:{start.isoformat()},until-pub-date:{end.isoformat()}",
                "rows": 1,
                "mailto": mailto,
            }
            try:
                response = client.get_json(api["base_url"], params, cache_key=f"crossref_{topic_id}_{start}_{end}")
            except Exception as exc:  # noqa: BLE001 - collection must preserve partial progress
                LOGGER.warning("CrossRef request failed for %s %s..%s: %s", topic_id, start, end, exc)
                results.append(
                    {
                        "source": "crossref",
                        "topic_id": topic_id,
                        "topic_label": topic["label"],
                        "window_start": start.isoformat(),
                        "window_end": end.isoformat(),
                        "activity_count": None,
                        "collection_status": "failed",
                        "error": str(exc),
                    }
                )
                continue
            message = response.payload.get("message", {})
            count = int(message.get("total-results", 0))
            results.append(
                {
                    "source": "crossref",
                    "topic_id": topic_id,
                    "topic_label": topic["label"],
                    "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                    "activity_count": count,
                    "collection_status": "ok",
                    "collected_at": response.fetched_at,
                }
            )
    return results


def write_records(records: list[dict[str, Any]], path: str | Path) -> Path:
    """Write newline-delimited JSON records."""

    import json

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return output
