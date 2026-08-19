"""Unified search tool routing to different sources.

Provides a single function `search` that returns normalized activity
records for downstream processing.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv

from config import PipelineConfig, generate_monthly_windows
from data_collectors.openalex_client import collect_openalex_topic
from data_collectors.gdelt_client import collect_gdelt_topic
from tools.github_client import fetch_github_trending


def _load_sources_config(attempt_root: Path) -> dict[str, Any]:
    """Load sources.yaml configuration."""
    sources_yaml = attempt_root / "configs" / "sources.yaml"
    if sources_yaml.exists():
        with open(sources_yaml, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def search(
    source: Literal["openalex", "gdelt", "github"],
    topic_id: str,
    topic_label: str,
    query: str,
    cfg: PipelineConfig,
    attempt_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Dispatch and return normalized records.

    - openalex/gdelt: monthly activity_count per window
    - github: daily snapshots written; return aggregated lightweight records (date-scoped)
    """
    if source in ("openalex", "gdelt"):
        windows = generate_monthly_windows(cfg.start_date, cfg.end_date)
        if source == "openalex":
            return collect_openalex_topic(
                topic_id=topic_id,
                topic_label=topic_label,
                query=query,
                windows=windows,
                cache_dir=cfg.raw_api_path / "openalex",
            )
        else:
            return collect_gdelt_topic(
                topic_id=topic_id,
                topic_label=topic_label,
                query=query,
                windows=windows,
                cache_dir=cfg.raw_api_path / "gdelt",
            )

    if source == "github":
        if attempt_root is None:
            attempt_root = Path(__file__).resolve().parents[3]
        
        # Load GitHub config from sources.yaml
        sources_cfg = _load_sources_config(attempt_root)
        gh_cfg = sources_cfg.get("sources", {}).get("github", {})
        
        k_new = gh_cfg.get("k_new", 100)
        k_active = gh_cfg.get("k_active", 50)
        lang_whitelist = gh_cfg.get("language_whitelist") or None
        org_whitelist = gh_cfg.get("org_whitelist") or None
        
        # Fetch trending snapshots (writes Interim), and emit one synthetic record
        summary = fetch_github_trending(
            attempt_root=attempt_root,
            raw_cache_dir=cfg.raw_api_path / "github",
            interim_dir=cfg.interim_path,
            k_new=k_new,
            k_active=k_active,
            language_whitelist=lang_whitelist,
            org_whitelist=org_whitelist,
        )
        return [{
            "source": "github",
            "topic_id": topic_id,
            "topic_label": topic_label,
            "window_start": summary["date"],  # day-level snapshot
            "window_end": summary["date"],
            "activity_count": summary["signals_count"],
            "features": {
                "repos_snapshot": summary["repos_snapshot"],
                "signals_snapshot": summary["signals_snapshot"],
            },
        }]

    raise ValueError(f"Unknown source: {source}")
