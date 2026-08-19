"""DataCollectionAgent orchestrates multi-source collection and persistence.

- Iterates topics and enabled sources
- Uses SearchTool to collect
- Writes a simple collection_report.json into Reports
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from config import PipelineConfig, ensure_dirs
from tools.search_tool import search
from processors.normalize import save_records_to_jsonl
from agents.base_agent import BaseAgent, AgentResult


@dataclass
class AgentOptions:
    sources_cfg_path: Path


class DataCollectionAgent(BaseAgent):
    def __init__(self, cfg: PipelineConfig, opts: AgentOptions) -> None:
        self.cfg = cfg
        self.opts = opts

    def _load_sources_cfg(self) -> dict[str, Any]:
        with open(self.opts.sources_cfg_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def run(self) -> AgentResult:
        ensure_dirs(self.cfg)
        sources_cfg = self._load_sources_cfg().get("sources", {})
        attempt_root = self.opts.sources_cfg_path.parent.parent.parent

        report = {
            "dataset": self.cfg.dataset_name,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "by_topic": [],
        }

        # Accumulate records by source for batch persistence
        all_openalex: list[dict[str, Any]] = []
        all_gdelt: list[dict[str, Any]] = []

        for topic in self.cfg.topics:
            entry = {"topic_id": topic.topic_id, "topic_label": topic.topic_label, "sources": {}}

            # OpenAlex
            if sources_cfg.get("openalex", {}).get("enabled", True):
                try:
                    recs = search(
                        source="openalex",
                        topic_id=topic.topic_id,
                        topic_label=topic.topic_label,
                        query=topic.openalex_query,
                        cfg=self.cfg,
                        attempt_root=attempt_root,
                    )
                    all_openalex.extend(recs)
                    entry["sources"]["openalex"] = {"records": len(recs)}
                except Exception as e:  # noqa: BLE001
                    entry["sources"]["openalex"] = {"error": str(e)}

            # GDELT
            if sources_cfg.get("gdelt", {}).get("enabled", True):
                try:
                    recs = search(
                        source="gdelt",
                        topic_id=topic.topic_id,
                        topic_label=topic.topic_label,
                        query=topic.gdelt_query,
                        cfg=self.cfg,
                        attempt_root=attempt_root,
                    )
                    all_gdelt.extend(recs)
                    entry["sources"]["gdelt"] = {"records": len(recs)}
                except Exception as e:  # noqa: BLE001
                    entry["sources"]["gdelt"] = {"error": str(e)}

            # GitHub
            gh_cfg = sources_cfg.get("github", {})
            if gh_cfg.get("enabled", True):
                try:
                    recs = search(
                        source="github",
                        topic_id=topic.topic_id,
                        topic_label=topic.topic_label,
                        query=topic.topic_label,  # placeholder: mapping to topic later if needed
                        cfg=self.cfg,
                        attempt_root=attempt_root,
                    )
                    entry["sources"]["github"] = {
                        "records": len(recs),
                        "date": recs[0]["window_start"] if recs else None,
                    }
                except Exception as e:  # noqa: BLE001
                    entry["sources"]["github"] = {"error": str(e)}

            report["by_topic"].append(entry)

        # Persist collected records to interim
        if all_openalex:
            save_records_to_jsonl(all_openalex, self.cfg.interim_path / "openalex_records.jsonl")
        if all_gdelt:
            save_records_to_jsonl(all_gdelt, self.cfg.interim_path / "gdelt_records.jsonl")

        report["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        out = self.cfg.reports_path / "collection_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return AgentResult(ok=True, detail={"report_path": str(out)})
