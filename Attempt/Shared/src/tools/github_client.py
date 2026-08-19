"""GitHub REST client for trending repository signals (public only).

- Uses search/repositories endpoint with two windows:
  1) created:>=D-7 sorted by stars desc (new repos)
  2) pushed:>=D-1 sorted by stars desc (active repos)
- Supports optional authentication via GITHUB_TOKEN
- Caches raw responses and writes minimal interim JSONL records
- Derives simple signals and (optionally) labels/summaries (rules-first)
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv

GITHUB_API = "https://api.github.com"
SEARCH_REPOS = f"{GITHUB_API}/search/repositories"
TIMEOUT = 60

USER_AGENT = "PredictiveAgents/0.1 (public research)"

# Default paging
PER_PAGE = 30  # GitHub max 100; smaller reduces rate pressure
SLEEP_AUThed = 0.4
SLEEP_UNAUThed = 1.5
MAX_PAGES = 4  # safety cap per query kind


def _load_env(attempt_root: Path) -> None:
    env_path = attempt_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        low = token.lower()
        # Fine-grained and OAuth tokens typically start with github_pat_, ghu_, ghs_, gho_
        use_bearer = low.startswith(("github_pat_", "ghu_", "ghs_", "gho_"))
        scheme = "Bearer" if use_bearer else "token"
        headers["Authorization"] = f"{scheme} {token}"
    return headers


def _rate_sleep() -> float:
    return SLEEP_AUThed if os.environ.get("GITHUB_TOKEN") else SLEEP_UNAUThed


def _cache_key(url: str, params: dict[str, Any]) -> str:
    raw = json.dumps({"url": url, "params": params}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


def _day_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _iso_to_dt(s: str) -> datetime:
    # 2024-01-01T12:34:56Z
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _ensure_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def _extract_minimal_repo(item: dict[str, Any]) -> dict[str, Any]:
    owner = item.get("owner") or {}
    license_info = item.get("license") or {}
    return {
        "repo_id": item.get("id"),
        "full_name": item.get("full_name"),
        "html_url": item.get("html_url"),
        "description": item.get("description"),
        "language": item.get("language"),
        "topics": item.get("topics", []),
        "stargazers_count": item.get("stargazers_count", 0),
        "forks_count": item.get("forks_count", 0),
        "open_issues_count": item.get("open_issues_count", 0),
        "watchers_count": item.get("watchers_count", 0),
        "license": license_info.get("key") if isinstance(license_info, dict) else None,
        "owner_login": owner.get("login"),
        "owner_type": owner.get("type"),
        "created_at": item.get("created_at"),
        "pushed_at": item.get("pushed_at"),
        "archived": item.get("archived", False),
        "disabled": item.get("disabled", False),
        "homepage": item.get("homepage"),
    }


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def _search_repos(params: dict[str, Any], cache_dir: Path) -> dict[str, Any]:
    key = _cache_key(SEARCH_REPOS, params)
    cpath = _cache_path(cache_dir, key)
    if cpath.exists():
        with open(cpath, "r", encoding="utf-8") as f:
            return json.load(f)

    headers = _headers()
    time.sleep(_rate_sleep())
    resp = requests.get(SEARCH_REPOS, headers=headers, params=params, timeout=TIMEOUT)
    if resp.status_code in (403, 429):
        # backoff linear * 3
        for i in range(3):
            wait = (i + 1) * 10
            print(f"    GitHub {resp.status_code}, retry in {wait}s...")
            time.sleep(wait)
            resp = requests.get(SEARCH_REPOS, headers=headers, params=params, timeout=TIMEOUT)
            if resp.ok:
                break
    resp.raise_for_status()
    data = resp.json()

    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def fetch_github_trending(
    attempt_root: Path,
    raw_cache_dir: Path,
    interim_dir: Path,
    k_new: int = 100,
    k_active: int = 50,
    language_whitelist: list[str] | None = None,
    org_whitelist: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch trending repos (two windows) and write interim JSONL snapshots.

    Returns a summary dict with counts and file paths.
    """
    _load_env(attempt_root)
    _ensure_dirs(raw_cache_dir, interim_dir)

    now = datetime.now(timezone.utc)
    day = _day_str(now)

    created_since = _day_str(now - timedelta(days=7))
    pushed_since = _day_str(now - timedelta(days=1))

    # Build queries
    q_new = f"created:>={created_since}"
    q_active = f"pushed:>={pushed_since}"

    results: list[dict[str, Any]] = []

    for q, topk, tag in [
        (q_new, k_new, "new"),
        (q_active, k_active, "active"),
    ]:
        page = 1
        kept = 0
        while kept < topk and page <= MAX_PAGES:
            per_page = min(PER_PAGE, topk - kept)
            params = {
                "q": q,
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            }
            data = _search_repos(params, raw_cache_dir)
            items = data.get("items", [])

            for item in items:
                rec = _extract_minimal_repo(item)
                if language_whitelist and rec.get("language") not in language_whitelist:
                    continue
                if org_whitelist and rec.get("owner_login") not in org_whitelist:
                    continue
                rec["_window"] = tag
                results.append(rec)
                kept += 1
                if kept >= topk:
                    break
            if not items:
                break
            page += 1

    # Deduplicate by repo_id keeping max stargazers_count
    seen: dict[int, dict[str, Any]] = {}
    for r in results:
        rid = int(r.get("repo_id") or 0)
        if rid not in seen or (r.get("stargazers_count", 0) > seen[rid].get("stargazers_count", 0)):
            seen[rid] = r
    deduped = list(seen.values())

    # Write interim repos snapshot
    repos_path = interim_dir / f"github_repos_{day}.jsonl"
    n_repos = _write_jsonl(repos_path, deduped)

    # Derive simple signals
    signals: list[dict[str, Any]] = []
    for r in deduped:
        created_at = r.get("created_at")
        pushed_at = r.get("pushed_at")
        stars = int(r.get("stargazers_count", 0))
        days = max(1, int((now - _iso_to_dt(created_at)).days)) if created_at else 1
        recent = 1 if (pushed_at and (now - _iso_to_dt(pushed_at)).days <= 3) else 0
        signals.append({
            "repo_id": r.get("repo_id"),
            "full_name": r.get("full_name"),
            "stars_total": stars,
            "stars_per_day_lifetime": round(stars / days, 3),
            "forks_total": int(r.get("forks_count", 0)),
            "activity_recent": recent,
            "language": r.get("language"),
            "created_at": created_at,  # Preserve for month extraction in analysis
            "_window": r.get("_window"),
        })

    signals_path = interim_dir / f"github_signals_{day}.jsonl"
    n_signals = _write_jsonl(signals_path, signals)

    return {
        "date": day,
        "repos_snapshot": str(repos_path),
        "signals_snapshot": str(signals_path),
        "repos_count": n_repos,
        "signals_count": n_signals,
    }
