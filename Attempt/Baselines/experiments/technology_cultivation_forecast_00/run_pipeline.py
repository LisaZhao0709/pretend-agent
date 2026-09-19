"""Run the full data pipeline using Shared agents and the baseline scoring.

This script orchestrates:
1. Data collection (CrossRef, OpenAlex, arXiv, GDELT, GitHub)
2. Data analysis (cleaning, anomaly detection, normalization)
3. Scoring (momentum-based + GitHub-aware)
4. Backtest evaluation

Output is saved to Data/Reports/technology_cultivation_00/
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Add Shared/src to path
SHARED_SRC = Path(__file__).resolve().parents[3] / "Shared" / "src"
sys.path.insert(0, str(SHARED_SRC))

# Add experiment src to path for scoring
EXP_SRC = Path(__file__).resolve().parents[0] / "src"
sys.path.insert(0, str(EXP_SRC))

from config import PipelineConfig, load_pipeline_config, generate_monthly_windows, month_range
from agents.data_collection_agent import DataCollectionAgent, AgentOptions as CollectionOptions
from agents.data_analysis_agent import DataAnalysisAgent
from scoring import evaluate_ranking, score_snapshot


SCORING_WEIGHTS = {
    "academic_weight": 0.4,
    "corporate_weight": 0.35,
    "community_weight": 0.25,
    "growth_weight": 0.45,
    "acceleration_weight": 0.25,
    "persistence_weight": 0.20,
    "level_weight": 0.10,
}


def main() -> None:
    # Load configuration
    attempt_root = Path(__file__).resolve().parents[3]
    config_path = attempt_root / "configs" / "default.yaml"
    topics_path = attempt_root / "configs" / "topics.yaml"
    sources_path = attempt_root / "configs" / "sources.yaml"

    cfg = load_pipeline_config(config_path=config_path, topics_path=topics_path)

    import yaml
    with open(sources_path, "r", encoding="utf-8") as f:
        sources_raw = yaml.safe_load(f)
    sources = sources_raw.get("sources", {})

    print(f"Project root: {cfg.data_root}")
    print(f"Interim path: {cfg.interim_path}")
    print(f"Processed path: {cfg.processed_path}")
    print(f"Reports path: {cfg.reports_path}")
    print(f"Topics: {len(cfg.topics)}")
    print(f"Sources enabled: {[s for s, enabled in sources.items() if enabled.get('enabled', False)]}")
    print()

    # Step 1: Data collection
    print("=== Step 1: Data Collection ===")
    collection_agent = DataCollectionAgent(cfg, CollectionOptions(sources_cfg_path=sources_path))
    collection_result = collection_agent.run()
    print(f"Collection result: {collection_result.ok}")
    if not collection_result.ok:
        print(f"Error: {collection_result.detail}")
        return
    print(f"Detail: {collection_result.detail}")
    print()

    # Step 2: Data analysis (cleaning, anomaly detection, normalization)
    print("=== Step 2: Data Analysis ===")
    analysis_agent = DataAnalysisAgent(cfg)
    analysis_result = analysis_agent.run()
    print(f"Analysis result: {analysis_result.ok}")
    if not analysis_result.ok:
        print(f"Error: {analysis_result.detail}")
        return
    print(f"Detail: {analysis_result.detail}")
    print()

    # Step 3: Scoring
    print("=== Step 3: Scoring ===")
    pivot_path = cfg.processed_path / "pivot_table_extended.jsonl"
    if not pivot_path.exists():
        print(f"Error: Pivot table not found at {pivot_path}")
        return

    from scoring import read_records
    pivot_records = read_records(pivot_path)
    print(f"Loaded {len(pivot_records)} pivot records")

    # Convert pivot to scoring format (each source as separate record)
    scoring_records = []
    for rec in pivot_records:
        for src in ["crossref", "openalex", "arxiv", "uspto", "gdelt", "github"]:
            count_col = f"{src}_count"
            if count_col in rec and rec[count_col] > 0:
                scoring_records.append({
                    "source": src,
                    "topic_id": rec["topic_id"],
                    "topic_label": rec["topic_label"],
                    "window_start": rec["window_start"],
                    "window_end": rec["window_end"],
                    "activity_count": rec[count_col],
                    "collection_status": "ok",
                })

    print(f"Converted to {len(scoring_records)} scoring records")

    if not scoring_records:
        print("No scoring records available (all counts are zero)")
        return

    ranking = score_snapshot(scoring_records, SCORING_WEIGHTS, sources)
    print(f"Ranked {len(ranking)} topics")
    for item in ranking[:3]:
        print(f"  {item['topic_label']}: joint_score={item.get('joint_score', 'N/A'):.3f}, data_status={item['data_status']}")
    print()

    # Save ranking
    ranking_path = cfg.reports_path / "forecast_ranking_latest.json"
    ranking_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ranking_path, "w", encoding="utf-8") as f:
        json.dump(ranking, f, ensure_ascii=False, indent=2)
    print(f"Saved ranking to {ranking_path}")
    print()

    # Step 4: Backtest (simplified: use available windows)
    print("=== Step 4: Backtest ===")
    # Group by window_end
    by_window_end: dict[str, list[dict]] = {}
    for rec in scoring_records:
        by_window_end.setdefault(rec["window_end"], []).append(rec)

    window_ends = sorted(by_window_end.keys())
    if len(window_ends) < 3:
        print(f"Not enough windows for backtest: {len(window_ends)}")
        return

    evaluations = []
    for i in range(1, len(window_ends) - 1):
        history_end = window_ends[i]
        history = [rec for rec in scoring_records if rec["window_end"] <= history_end]
        future_end = window_ends[i + 1]
        future = [rec for rec in scoring_records if rec["window_end"] == future_end]

        if not history or not future:
            continue

        predictions = score_snapshot(history, SCORING_WEIGHTS, sources)
        eval_result = evaluate_ranking(predictions, future, sources)
        evaluations.append({
            "history_end": history_end,
            "future_end": future_end,
            **eval_result,
        })

    print(f"Evaluated {len(evaluations)} windows")
    for eval_item in evaluations:
        print(f"  {eval_item['history_end']} -> {eval_item['future_end']}: {eval_item['status']}, top1={eval_item.get('top1_topic_id', 'N/A')}")
    print()

    # Save backtest
    backtest_path = cfg.reports_path / "backtest_latest.json"
    with open(backtest_path, "w", encoding="utf-8") as f:
        json.dump(evaluations, f, ensure_ascii=False, indent=2)
    print(f"Saved backtest to {backtest_path}")
    print()

    print("=== Pipeline Complete ===")
    print(f"Reports saved to {cfg.reports_path}")


if __name__ == "__main__":
    main()
