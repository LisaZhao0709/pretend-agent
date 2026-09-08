"""OpenAlex Works API collector.

Uses ``per_page=1`` and reads ``meta.count`` to get the publication count in
a single small request per (topic, month) window. This avoids the
``group_by=publication_date`` endpoint which returns 400 / empty results.

OpenAlex now uses a freemium model: $1/day free budget, search calls cost
$0.001 each. With 6 topics x 31 months = 186 calls = $0.186/day, well within
the free tier. An API key (free to obtain at openalex.org) raises the daily
budget 10x and avoids rate limiting.

The per-month loop, caching, retry, and failure handling are inherited from
:class:`~data_collectors.base.MonthCountCollector`. This file only defines the
4 OpenAlex-specific hooks.
"""

from __future__ import annotations

import os
from typing import Any

from data_collectors.base import register, MonthCountCollector
from http_client import CachedResponse

OPENALEX_BASE_URL = "https://api.openalex.org/works"


@register("openalex")
class OpenAlexCollector(MonthCountCollector):
    """Monthly publication-count collector for OpenAlex Works API."""

    base_url = OPENALEX_BASE_URL

    def build_params(self, query: str, date_start: str, date_end: str, contact: str) -> dict[str, Any]:
        params: dict[str, Any] = {
            "search": query,
            "filter": f"from_publication_date:{date_start},to_publication_date:{date_end}",
            "per_page": 1,
            "mailto": contact,
        }
        # Add API key if available (raises daily free budget 10x)
        api_key = os.getenv("OPENALEX_API_KEY", "")
        if api_key:
            params["api_key"] = api_key
        return params

    def parse_count(self, response: CachedResponse) -> int:
        meta = response.payload.get("meta", {}) if isinstance(response.payload, dict) else {}
        return int(meta.get("count", 0))

    def resolve_contact(self, source_cfg: dict[str, Any]) -> str:
        env_name = source_cfg.get("email_env", "OPENALEX_EMAIL")
        return os.getenv(env_name, source_cfg.get("email", "research@example.com"))
