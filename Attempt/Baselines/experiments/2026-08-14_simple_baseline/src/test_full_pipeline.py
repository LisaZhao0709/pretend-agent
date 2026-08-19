"""Integration test: full pipeline with GitHub signals.

Runs:
1. DataCollectionAgent (OpenAlex, GDELT, GitHub)
2. DataAnalysisAgent (merge + quality check)
3. Baseline forecasting (on extended pivot)
4. Evaluation
5. Report generation (if quality sufficient)

Usage:
    python -m Baselines.experiments.2026-08-14_simple_baseline.src.test_full_pipeline
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ATTEMPT_ROOT = Path(__file__).resolve().parents[4]
LOCAL_SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(ATTEMPT_ROOT / "Shared" / "src"))
sys.path.insert(0, str(ATTEMPT_ROOT))
sys.path.insert(0, str(LOCAL_SRC))

from config import load_pipeline_config, generate_monthly_windows
from agents.data_collection_agent import DataCollectionAgent, AgentOptions
from agents.data_analysis_agent import DataAnalysisAgent
from baseline_model import forecast_topic
from evaluator import evaluate_forecast, summarize_results
from processors.normalize import load_jsonl
from report_generator import generate_report


def main() -> None:
    print("Full Pipeline Test: Collection → Analysis → Forecast → Report")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    cfg = load_pipeline_config()

    # Phase 1: Collection
    print("=" * 60)
    print("Phase 1: DataCollectionAgent")
    print("=" * 60)
    agent1 = DataCollectionAgent(cfg, AgentOptions(sources_cfg_path=ATTEMPT_ROOT / "configs" / "sources.yaml"))
    res1 = agent1.run()
    print(f"Status: {'✓' if res1.ok else '✗'}")
    if not res1.ok:
        print(f"Error: {res1.detail}")
        return
    print()

    # Phase 2: Analysis
    print("=" * 60)
    print("Phase 2: DataAnalysisAgent")
    print("=" * 60)
    agent2 = DataAnalysisAgent(cfg)
    res2 = agent2.run()
    print(f"Status: {'✓' if res2.ok else '✗'}")
    if not res2.ok:
        print(f"Error: {res2.detail}")
        return
    print(f"Pivot records: {res2.detail['pivot_records']}")
    print(f"Quality score: {res2.detail['quality_score']}/100")
    print()

    # Phase 3: Baseline Forecast
    print("=" * 60)
    print("Phase 3: Baseline Forecasting")
    print("=" * 60)
    pivot_path = cfg.processed_path / "pivot_table_extended.jsonl"
    if not pivot_path.exists():
        print("No pivot table found")
        return

    pivot = load_jsonl(pivot_path)
    windows = generate_monthly_windows(cfg.start_date, cfg.end_date)

    # Group by topic
    by_topic: dict[str, list[dict]] = {}
    for rec in pivot:
        tid = rec.get("topic_id")
        if tid not in by_topic:
            by_topic[tid] = []
        by_topic[tid].append(rec)

    all_results = {}
    all_evals = {}

    for topic in cfg.topics:
        recs = by_topic.get(topic.topic_id, [])
        if not recs:
            print(f"  {topic.topic_id}: no data")
            continue

        # Use GDELT + GitHub as features (skip OpenAlex due to 429 errors)
        result = forecast_topic(
            topic_id=topic.topic_id,
            records=recs,
            windows=windows,
            feature_cols=["gdelt_count", "github_stars_total"],
        )
        all_results[topic.topic_id] = result

        evals = evaluate_forecast(result)
        all_evals[topic.topic_id] = evals
        print(f"  {topic.topic_id}: MAE={evals['ma']['mae']:.2f}, MAPE={evals['ma']['mape']:.2f}%")

    summary = summarize_results(all_evals)
    print(f"\nOverall: MAE={summary['overall']['mae']:.2f}, MAPE={summary['overall']['mape']:.2f}%")
    print()

    # Phase 4: Report
    print("=" * 60)
    print("Phase 4: AI Report Generation")
    print("=" * 60)
    try:
        report_path = generate_report(cfg.reports_path, ATTEMPT_ROOT)
        print(f"Report: {report_path}")
    except Exception as e:  # noqa: BLE001
        print(f"Report skipped: {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()
