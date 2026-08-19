"""A polite, cache-first HTTP client for public research APIs."""

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
    """Minimal response representation persisted in the raw API cache."""

    status_code: int
    headers: dict[str, str]
    payload: Any
    fetched_at: str
    url: str


class PoliteApiClient:
    """Cache-first client with spacing, Retry-After, and bounded backoff."""

    def __init__(self, cache_dir: str | Path, settings: dict[str, Any]) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.settings = settings
        self.session = requests.Session()
        user_agent = settings["user_agent"]
        email_env = settings.get("contact_email_env")
        if email_env and os.getenv(email_env):
            user_agent = f"{user_agent} (mailto:{os.environ[email_env]})"
        self.session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
        self._last_request_at = 0.0
        self.request_log_path = self.cache_dir / "request_log_00.jsonl"

    def get_json(self, url: str, params: dict[str, Any], *, cache_key: str) -> CachedResponse:
        """GET JSON with a deterministic cache key and bounded retries."""

        cache_path = self.cache_dir / f"{self._cache_name(url, params, cache_key)}.json"
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as handle:
                return CachedResponse(**json.load(handle))

        max_retries = int(self.settings["max_retries"])
        for attempt in range(max_retries + 1):
            self._wait_for_spacing()
            try:
                response = self.session.get(url, params=params, timeout=float(self.settings["timeout_seconds"]))
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
            result = CachedResponse(
                status_code=response.status_code,
                headers={key: value for key, value in response.headers.items() if key.lower() in {"date", "etag", "retry-after"}},
                payload=response.json(),
                fetched_at=datetime.now(UTC).isoformat(),
                url=self._redact_url(response.url),
            )
            with cache_path.open("w", encoding="utf-8") as handle:
                json.dump(asdict(result), handle, ensure_ascii=False, indent=2)
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
            delay = float(self.settings["backoff_factor_seconds"]) * (2**attempt)
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
            safe_query.append((key, "[REDACTED]" if key.lower() in {"api_key", "apikey", "key", "token"} else value))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(safe_query), parts.fragment))

    @staticmethod
    def _cache_name(url: str, params: dict[str, Any], cache_key: str) -> str:
        query = json.dumps({"url": url, "params": params, "cache_key": cache_key}, sort_keys=True)
        return hashlib.sha256(query.encode("utf-8")).hexdigest()
