"""Unified polite HTTP client for all data collectors.

Provides a single cache-first HTTP layer with:
- Deterministic cache keys (full 64-char SHA256)
- Bounded retries with exponential backoff + jitter
- Respect for Retry-After headers
- Non-JSON response wrapping (e.g. GDELT plain-text errors)
- Per-cache request logging
- URL redaction for api_key/token query params

All collectors in ``data_collectors/`` MUST go through this client so that
cache format, retry behaviour, and error handling stay consistent across
sources and across the Shared + Baseline pipelines.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests


class RateLimitedError(requests.HTTPError):
    """Raised when a provider asks for a wait longer than this run permits."""

    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class CachedResponse:
    """Minimal response representation persisted in the raw API cache.

    This is the single canonical cache format for every source. Older
    ``{"url", "params", "fetched_at", "response"}`` records are not readable
    by this client and must be regenerated.

    ``cache_hit`` is True when the value came from disk cache rather than a
    live network request. It is NOT persisted to the cache file (it is only
    meaningful for the in-memory result of the current call), so callers
    reading old cache files will see the default False.
    """

    status_code: int
    headers: dict[str, str]
    payload: Any
    fetched_at: str
    url: str
    cache_hit: bool = False


# Default HTTP settings. Per-source overrides come from sources.yaml["http"].
DEFAULT_HTTP_SETTINGS: dict[str, Any] = {
    "user_agent": "PredictiveAgents/0.1 (research project)",
    "contact_email_env": "PROJECT_CONTACT_EMAIL",
    "timeout_seconds": 30,
    "max_retries": 3,
    "min_interval_seconds": 3.0,
    "backoff_factor_seconds": 15.0,
    "max_backoff_seconds": 90.0,
    "max_retry_after_seconds": 120.0,
    "jitter_seconds": 1.5,
    "respect_retry_after": True,
}


class PoliteApiClient:
    """Cache-first client with spacing, Retry-After, and bounded backoff."""

    def __init__(self, cache_dir: str | Path, settings: dict[str, Any] | None = None) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # Merge defaults with caller overrides (caller wins).
        merged = dict(DEFAULT_HTTP_SETTINGS)
        if settings:
            merged.update(settings)
        self.settings = merged
        self.session = requests.Session()
        user_agent = merged["user_agent"]
        email_env = merged.get("contact_email_env")
        if email_env and os.getenv(email_env):
            user_agent = f"{user_agent} (mailto:{os.environ[email_env]})"
        self.session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
        self._last_request_at = 0.0
        self.request_log_path = self.cache_dir / "request_log_00.jsonl"

    def get_json(
        self,
        url: str,
        params: dict[str, Any],
        *,
        cache_key: str,
        extra_headers: dict[str, str] | None = None,
    ) -> CachedResponse:
        """GET JSON with a deterministic cache key and bounded retries.

        Args:
            url: Base URL (without query string).
            params: Query parameters.
            cache_key: Deterministic suffix appended to the hashed cache name
                so callers can use human-readable identifiers (e.g.
                ``crossref_llm_2023-01_2023-02``) alongside the url+params hash.
            extra_headers: Optional per-request headers (e.g. GitHub Accept).

        Returns:
            A ``CachedResponse``. Non-JSON bodies are wrapped as
            ``{"_non_json_body": text[:500]}`` so callers can detect and
            record them as failures instead of silently treating them as empty.
        """
        cache_path = self.cache_dir / f"{self._cache_name(url, params, cache_key)}.json"
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            # Old cache files lack cache_hit; default to True for disk hits.
            data.setdefault("cache_hit", True)
            return CachedResponse(**data)

        max_retries = int(self.settings["max_retries"])
        for attempt in range(max_retries + 1):
            self._wait_for_spacing()
            try:
                if extra_headers:
                    response = self.session.get(
                        url, params=params, timeout=float(self.settings["timeout_seconds"]),
                        headers={**self.session.headers, **extra_headers},
                    )
                else:
                    response = self.session.get(
                        url, params=params, timeout=float(self.settings["timeout_seconds"]),
                    )
            except requests.RequestException:
                self._log_attempt(url, None, attempt, "request_exception")
                if attempt >= max_retries:
                    raise
                self._backoff(attempt, retry_after=None)
                continue

            self._log_attempt(response.url, response.status_code, attempt, "response")
            if response.status_code == 429:
                retry_after = self._retry_after_seconds(response.headers.get("Retry-After"))
                maximum = float(self.settings.get("max_retry_after_seconds", 60.0))
                if retry_after is not None and retry_after > maximum:
                    raise RateLimitedError(
                        f"Provider requested waiting {retry_after:.1f}s; stopping instead of retrying early",
                        retry_after_seconds=retry_after,
                    )
                if attempt >= max_retries:
                    response.raise_for_status()
                self._backoff(attempt, retry_after=response.headers.get("Retry-After"))
                continue

            if response.status_code >= 500:
                if attempt >= max_retries:
                    response.raise_for_status()
                self._backoff(attempt, retry_after=response.headers.get("Retry-After"))
                continue

            response.raise_for_status()
            try:
                payload = response.json()
            except (ValueError, json.JSONDecodeError):
                # Provider returned a non-JSON body (e.g. GDELT returns plain-text
                # error messages). Wrap it so callers can inspect it.
                payload = {"_non_json_body": response.text[:500]}
            result = CachedResponse(
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items()
                         if k.lower() in {"date", "etag", "retry-after"}},
                payload=payload,
                fetched_at=datetime.now(UTC).isoformat(),
                url=self._redact_url(response.url),
                cache_hit=False,
            )
            # Persist without cache_hit (it is only meaningful in-memory).
            persist = {k: v for k, v in asdict(result).items() if k != "cache_hit"}
            with cache_path.open("w", encoding="utf-8") as handle:
                json.dump(persist, handle, ensure_ascii=False, indent=2)
            return result

        raise RuntimeError("API request exhausted retries without a response")

    def _wait_for_spacing(self) -> None:
        minimum = float(self.settings["min_interval_seconds"])
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < minimum:
            time.sleep(minimum - elapsed)
        self._last_request_at = time.monotonic()

    def _backoff(self, attempt: int, retry_after: str | None) -> None:
        if self.settings.get("respect_retry_after", True) and retry_after:
            try:
                delay = float(retry_after)
            except ValueError:
                delay = 0.0
        else:
            delay = float(self.settings["backoff_factor_seconds"]) * (2 ** attempt)
        delay = min(delay, float(self.settings["max_backoff_seconds"]))
        delay += random.uniform(0, float(self.settings["jitter_seconds"]))
        time.sleep(delay)

    @staticmethod
    def _retry_after_seconds(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            return None

    def _log_attempt(self, url: str, status_code: int | None, attempt: int, event: str) -> None:
        entry = {
            "event": event,
            "attempt": attempt,
            "status_code": status_code,
            "url": self._redact_url(url),
            "logged_at": datetime.now(UTC).isoformat(),
        }
        with self.request_log_path.open("a", encoding="utf-8") as handle:
            json.dump(entry, handle, ensure_ascii=False)
            handle.write("\n")

    @staticmethod
    def _redact_url(url: str) -> str:
        if not url:
            return url
        parts = urlsplit(url)
        safe_query = []
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            safe_query.append(
                (key, "[REDACTED]" if key.lower() in {"api_key", "apikey", "key", "token"} else value)
            )
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(safe_query), parts.fragment))

    @staticmethod
    def _cache_name(url: str, params: dict[str, Any], cache_key: str) -> str:
        query = json.dumps({"url": url, "params": params, "cache_key": cache_key}, sort_keys=True)
        return hashlib.sha256(query.encode("utf-8")).hexdigest()
