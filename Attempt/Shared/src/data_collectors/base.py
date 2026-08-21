"""Source collector interface and registry.

Every data source implements :class:`SourceCollector` so that
``DataCollectionAgent`` can iterate sources purely from ``sources.yaml``
configuration instead of hardcoding per-source branches.

A collector receives:
- ``cfg``: the validated :class:`~config.PipelineConfig`
- ``http_settings``: the ``http`` section of ``sources.yaml`` (or defaults)
- ``source_cfg``: the per-source section of ``sources.yaml`` (e.g. mailto,
  k_new, language_whitelist)

and returns a list of activity records. Each record MUST carry:

- ``source``: short source name (``"crossref"`` etc.)
- ``topic_id`` / ``topic_label``
- ``window_start`` / ``window_end`` (YYYY-MM for academic/news, YYYY-MM-DD for
  daily snapshots)
- ``activity_count``: int or ``None`` when the request failed
- ``collection_status``: ``"ok"`` or ``"failed"``
- ``collected_at``: ISO timestamp
- ``error``: present only when ``collection_status == "failed"``
- ``cached``: bool, whether the value came from cache
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from config import PipelineConfig, generate_monthly_windows, month_range
from http_client import PoliteApiClient, CachedResponse


@runtime_checkable
class SourceCollector(Protocol):
    """Unified interface for every data source collector."""

    source_name: str

    def collect(
        self,
        cfg: PipelineConfig,
        http_settings: dict[str, Any],
        source_cfg: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Collect activity records for all enabled topics and windows.

        Returns a flat list of records (see module docstring for the schema).
        Per-window failures are returned as ``collection_status == "failed"``
        records rather than raised, so partial progress is preserved.
        """
        ...


_REGISTRY: dict[str, SourceCollector] = {}


def register(source_name: str) -> Any:
    """Class decorator: register a collector under ``source_name``."""

    def decorator(cls: Any) -> Any:
        cls.source_name = source_name
        _REGISTRY[source_name] = cls()
        return cls

    return decorator


def get_collector(source_name: str) -> SourceCollector:
    """Look up a registered collector by source name."""
    try:
        return _REGISTRY[source_name]
    except KeyError as exc:
        raise ValueError(f"Unknown source: {source_name!r}. Registered: {sorted(_REGISTRY)}") from exc


def registered_sources() -> list[str]:
    """Return the sorted list of registered source names."""
    return sorted(_REGISTRY)


class MonthCountCollector:
    """Base for sources that fetch one count per (topic, month) window.

    Implements the full ``collect()`` loop: iterate topics x months, build
    params, call :class:`~http_client.PoliteApiClient`, handle failures, and
    emit records. Subclasses only override the 4 hooks that differ per source:

    - :attr:`base_url`: API endpoint
    - :meth:`build_params`: how to assemble query parameters
    - :meth:`parse_count`: how to read the count from the response
    - :meth:`resolve_contact`: how to get the polite-pool email (if any)

    ``source_name`` is set by the ``@register`` decorator at import time.
    """

    base_url: str = ""

    def collect(
        self,
        cfg: PipelineConfig,
        http_settings: dict[str, Any],
        source_cfg: dict[str, Any],
    ) -> list[dict[str, Any]]:
        windows = generate_monthly_windows(cfg.start_date, cfg.end_date)
        if not windows:
            return []

        cache_dir = cfg.raw_api_path / self.source_name
        client = PoliteApiClient(cache_dir, http_settings)
        contact = self.resolve_contact(source_cfg)
        records: list[dict[str, Any]] = []

        for topic in cfg.topics:
            query = self.get_topic_query(topic)
            for w_start, w_end in windows:
                date_start, date_end = month_range(w_start)
                params = self.build_params(query, date_start, date_end, contact)
                cache_key = f"{self.source_name}_{topic.topic_id}_{w_start}_{w_end}"
                try:
                    response = client.get_json(self.base_url, params, cache_key=cache_key)
                except Exception as exc:  # noqa: BLE001 - preserve partial progress
                    records.append(self._failed_record(topic, w_start, w_end, exc))
                    continue

                if isinstance(response.payload, dict) and "_non_json_body" in response.payload:
                    records.append(self._failed_record(
                        topic, w_start, w_end,
                        RuntimeError(f"non-JSON response: {response.payload['_non_json_body'][:120]}"),
                    ))
                    continue

                records.append({
                    "source": self.source_name,
                    "topic_id": topic.topic_id,
                    "topic_label": topic.topic_label,
                    "window_start": w_start,
                    "window_end": w_end,
                    "activity_count": self.parse_count(response),
                    "collection_status": "ok",
                    "collected_at": response.fetched_at,
                    "cached": response.cache_hit,
                })

        return records

    # --- Hooks: subclasses override these 4 ---

    def build_params(self, query: str, date_start: str, date_end: str, contact: str) -> dict[str, Any]:
        """Assemble the API query parameters for one (topic, month) request."""
        raise NotImplementedError

    def parse_count(self, response: CachedResponse) -> int:
        """Extract the activity count from a successful API response."""
        raise NotImplementedError

    def resolve_contact(self, source_cfg: dict[str, Any]) -> str:
        """Return the polite-pool contact email (or empty string if N/A)."""
        return ""

    def get_topic_query(self, topic: Any) -> str:
        """Pick the right query string from the topic config. Default: openalex_query."""
        return topic.openalex_query

    # --- Shared helper ---

    def _failed_record(self, topic: Any, w_start: str, w_end: str, exc: Exception) -> dict[str, Any]:
        return {
            "source": self.source_name,
            "topic_id": topic.topic_id,
            "topic_label": topic.topic_label,
            "window_start": w_start,
            "window_end": w_end,
            "activity_count": None,
            "collection_status": "failed",
            "collected_at": datetime.utcnow().isoformat() + "Z",
            "cached": False,
            "error": str(exc),
        }
