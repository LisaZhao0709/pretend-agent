"""DataAnalysisAgent merges multi-source data and performs quality checks.

- Loads collected records from interim
- Merges OpenAlex, GDELT, GitHub into extended pivot table
- Runs quality checks
- Outputs pivot_table_extended.jsonl and quality_report.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from config import PipelineConfig
from processors.normalize import load_jsonl, create_pivot_table, save_records_to_jsonl
from processors.quality_checker import check_data_quality, save_quality_report
from agents.base_agent import BaseAgent, AgentResult


class DataAnalysisAgent(BaseAgent):
    def __init__(self, cfg: PipelineConfig) -> None:
        self.cfg = cfg

    def _load_github_signals(self) -> dict[str, dict[str, Any]]:
        """Load latest github_signals_YYYY-MM-DD.jsonl snapshot."""
        interim = self.cfg.interim_path
        if not interim.exists():
            return {}

        # Find latest github_signals file
        candidates = sorted(interim.glob("github_signals_*.jsonl"), reverse=True)
        if not candidates:
            return {}

        signals: dict[str, dict[str, Any]] = {}
        with open(candidates[0], "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    rid = rec.get("repo_id")
                    if rid:
                        signals[rid] = rec
        return signals

    def _extend_pivot_with_github(
        self,
        pivot: list[dict[str, Any]],
        gh_signals: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Add github_* columns to pivot table.

        GitHub signals are daily snapshots; we aggregate them by month to match pivot windows.
        """
        # Group signals by month (extract from created_at or use latest snapshot)
        gh_by_month: dict[str, list[dict[str, Any]]] = {}
        for sig in gh_signals.values():
            # Signals have created_at as YYYY-MM-DDTHH:MM:SSZ or similar; extract month
            date_str = sig.get("created_at", "")
            if date_str:
                month = date_str[:7]  # YYYY-MM
            else:
                # Fallback: use the snapshot date from _window or assume current month
                month = "unknown"
            if month not in gh_by_month:
                gh_by_month[month] = []
            gh_by_month[month].append(sig)

        # Extend pivot
        for row in pivot:
            month = row.get("window_start", "")
            sigs = gh_by_month.get(month, [])
            if sigs:
                row["github_stars_total"] = sum(s.get("stars_total", 0) for s in sigs)
                row["github_stars_per_day"] = sum(s.get("stars_per_day_lifetime", 0) for s in sigs)
                row["github_forks_total"] = sum(s.get("forks_total", 0) for s in sigs)
                row["github_activity_recent"] = sum(s.get("activity_recent", 0) for s in sigs)
            else:
                row["github_stars_total"] = 0
                row["github_stars_per_day"] = 0
                row["github_forks_total"] = 0
                row["github_activity_recent"] = 0

        return pivot

    def run(self) -> AgentResult:
        try:
            # Load collected records
            openalex_path = self.cfg.interim_path / "openalex_records.jsonl"
            gdelt_path = self.cfg.interim_path / "gdelt_records.jsonl"

            openalex_recs = load_jsonl(openalex_path) if openalex_path.exists() else []
            gdelt_recs = load_jsonl(gdelt_path) if gdelt_path.exists() else []

            # Merge and pivot
            from processors.normalize import merge_records_by_source
            merged = merge_records_by_source(openalex_recs, gdelt_recs)
            pivot = create_pivot_table(merged)

            # Load and merge GitHub signals
            gh_signals = self._load_github_signals()
            pivot = self._extend_pivot_with_github(pivot, gh_signals)

            # Save extended pivot
            pivot_path = self.cfg.processed_path / "pivot_table_extended.jsonl"
            n = save_records_to_jsonl(pivot, pivot_path)

            # Quality check
            quality = check_data_quality(pivot)
            quality_path = self.cfg.reports_path / "quality_report.json"
            save_quality_report(quality, quality_path)

            return AgentResult(
                ok=True,
                detail={
                    "pivot_records": n,
                    "pivot_path": str(pivot_path),
                    "quality_score": quality["overall_score"],
                    "quality_report_path": str(quality_path),
                },
            )
        except Exception as e:  # noqa: BLE001
            return AgentResult(ok=False, detail={"error": str(e)})
