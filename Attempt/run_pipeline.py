"""Run the full data pipeline using Shared agents and the baseline scoring.

This script orchestrates:
1. Data collection (CrossRef, OpenAlex, arXiv, GDELT, GitHub)
2. Data analysis (cleaning, anomaly detection, normalization)
3. Scoring (momentum-based + GitHub-aware)
4. Backtest evaluation

Output is saved to Data/Reports/technology_cultivation_00/

Usage:
    cd Attempt
    python -m run_pipeline
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Add Shared/src to path only
SHARED_SRC = Path(__file__).resolve().parent / "Shared" / "src"
sys.path.insert(0, str(SHARED_SRC))

# Import Shared modules
import config as shared_config
import agents.data_collection_agent as shared_dc_agent
import agents.data_analysis_agent as shared_da_agent

# Load experiment scoring module separately to avoid config name collision
EXP_SRC = Path(__file__).resolve().parent / "Baselines" / "experiments" / "technology_cultivation_forecast_01" / "src"
spec = importlib.util.spec_from_file_location("experiment_scoring", EXP_SRC / "scoring.py")
experiment_scoring = importlib.util.module_from_spec(spec)
sys.modules["experiment_scoring"] = experiment_scoring
spec.loader.exec_module(experiment_scoring)



def main() -> None:
    print("Initializing pipeline...")
    cfg = shared_config.load_pipeline_config()
    cfg.dataset_name = "technology_cultivation_01"
    
    opts = shared_dc_agent.AgentOptions(
        sources_cfg_path=Path(__file__).resolve().parent / "configs" / "sources.yaml"
    )

    # Step 1: Data Collection
    print("=== Step 1: Data Collection ===")
    collection_agent = shared_dc_agent.DataCollectionAgent(cfg, opts)
    collection_result = collection_agent.run()
    print(f"Collection result: {collection_result.ok}")
    if not collection_result.ok:
        print(f"Error: {collection_result.detail}")
        return
    print(f"Detail: {collection_result.detail}")
    print()

    # Step 2: Data Analysis
    print("=== Step 2: Data Analysis ===")
    analysis_agent = shared_da_agent.DataAnalysisAgent(cfg)
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

    pivot_records = experiment_scoring.read_records(pivot_path)
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

    scoring_cfg = {
        "ema_short_weight": 0.3,
        "macd_weight": 0.4,
        "stability_weight": 0.15,
        "persistence_weight": 0.15,
        "academic_weight": 0.4,
        "corporate_weight": 0.35,
        "community_weight": 0.25,
    }
    sources_cfg = shared_config.load_yaml_config(opts.sources_cfg_path).get("sources", {})
    ranking = experiment_scoring.score_snapshot(scoring_records, scoring_cfg, sources_cfg)
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

    evaluations_1m = []
    evaluations_3m = []

    for i in range(1, len(window_ends) - 1):
        history_end = window_ends[i]
        history = [rec for rec in scoring_records if rec["window_end"] <= history_end]
        if not history:
            continue

        predictions = experiment_scoring.score_snapshot(history, scoring_cfg, sources_cfg)

        # 1-month horizon evaluation
        future_1m_end = window_ends[i + 1]
        future_1m = [rec for rec in scoring_records if rec["window_end"] == future_1m_end]
        if future_1m:
            eval_1m = experiment_scoring.evaluate_ranking(predictions, future_1m, sources_cfg)
            evaluations_1m.append({
                "history_end": history_end,
                "future_end": future_1m_end,
                "horizon": "1m",
                **eval_1m,
            })

        # 3-month horizon evaluation
        if i + 3 < len(window_ends):
            future_3m_end = window_ends[i + 3]
            future_3m = [rec for rec in scoring_records if history_end < rec["window_end"] <= future_3m_end]
            if future_3m:
                eval_3m = experiment_scoring.evaluate_ranking(predictions, future_3m, sources_cfg)
                evaluations_3m.append({
                    "history_end": history_end,
                    "future_end": future_3m_end,
                    "horizon": "3m",
                    **eval_3m,
                })

    def _calc_summary(eval_list: list[dict[str, Any]]) -> dict[str, Any]:
        valid = [e for e in eval_list if e.get("status") == "ok"]
        if not valid:
            return {}
        rhos = [e["spearman_rho"] for e in valid if e.get("spearman_rho") is not None]
        ndcg3s = [e["ndcg@3"] for e in valid if e.get("ndcg@3") is not None]
        ndcg5s = [e["ndcg@5"] for e in valid if e.get("ndcg@5") is not None]
        lifts = [e["top1_lift"] for e in valid if e.get("top1_lift") is not None]
        return {
            "total_windows": len(eval_list),
            "valid_windows": len(valid),
            "mean_top1_lift": round(sum(lifts) / len(lifts), 4) if lifts else None,
            "mean_spearman_rho": round(sum(rhos) / len(rhos), 4) if rhos else None,
            "mean_ndcg@3": round(sum(ndcg3s) / len(ndcg3s), 4) if ndcg3s else None,
            "mean_ndcg@5": round(sum(ndcg5s) / len(ndcg5s), 4) if ndcg5s else None,
        }

    summary_1m = _calc_summary(evaluations_1m)
    summary_3m = _calc_summary(evaluations_3m)

    print(f"1-Month Horizon ({len(evaluations_1m)} windows): {summary_1m}")
    print(f"3-Month Horizon ({len(evaluations_3m)} windows): {summary_3m}")
    print()

    backtest_report = {
        "horizon_1m": {
            "summary": summary_1m,
            "windows": evaluations_1m,
        },
        "horizon_3m": {
            "summary": summary_3m,
            "windows": evaluations_3m,
        },
    }

    # Save backtest
    backtest_path = cfg.reports_path / "backtest_latest.json"
    with open(backtest_path, "w", encoding="utf-8") as f:
        json.dump(backtest_report, f, ensure_ascii=False, indent=2)
    print(f"Saved backtest to {backtest_path}")
    print()

    # Step 5: Final Reporting
    print("=== Step 5: Final Reporting ===")
    import agents.reporting_agent as shared_rp_agent
    reporting_agent = shared_rp_agent.ReportingAgent(cfg)
    reporting_agent.run()

    print("=== Pipeline Complete ===")
    print(f"Reports saved to {cfg.reports_path}")


if __name__ == "__main__":
    main()
