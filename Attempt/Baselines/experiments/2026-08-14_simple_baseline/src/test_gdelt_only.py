"""Quick test: run Phase 2-3 using only GDELT cached data (skip OpenAlex).

Usage:
    python -m Baselines.experiments.2026-08-14_simple_baseline.src.test_gdelt_only
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ATTEMPT_ROOT = Path(__file__).resolve().parents[4]
LOCAL_SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(ATTEMPT_ROOT / "Shared" / "src"))
sys.path.insert(0, str(ATTEMPT_ROOT))
sys.path.insert(0, str(LOCAL_SRC))

from config import (
    PipelineConfig,
    ensure_dirs,
    generate_monthly_windows,
    load_pipeline_config,
)
import yaml as _yaml
import data_collectors.gdelt  # noqa: F401 - registers collector
from data_collectors.base import get_collector
from processors.normalize import (
    create_pivot_table,
    merge_records_by_source,
    save_records_to_jsonl,
)
from baseline_model import forecast_topic
from evaluator import evaluate_forecast, summarize_results


def main() -> None:
    print("Predictive Agents — GDELT-Only Test Pipeline")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    cfg = load_pipeline_config()
    ensure_dirs(cfg)

    windows = generate_monthly_windows(cfg.start_date, cfg.end_date)

    # Phase 1: Collect GDELT only (uses cache)
    print("=" * 60)
    print("Phase 1: GDELT Data Collection (cached)")
    print("=" * 60)

    sources_yaml = ATTEMPT_ROOT / "configs" / "sources.yaml"
    raw_cfg = {}
    if sources_yaml.exists():
        with open(sources_yaml, "r", encoding="utf-8") as f:
            raw_cfg = _yaml.safe_load(f) or {}
    http_settings = raw_cfg.get("http", {})
    gdelt_cfg = raw_cfg.get("sources", {}).get("gdelt", {})

    all_gdelt: list[dict] = []
    collector = get_collector("gdelt")
    gd_records = collector.collect(cfg, http_settings, gdelt_cfg)
    cached_count = sum(1 for r in gd_records if r.get("cached"))
    ok_count = sum(1 for r in gd_records if r.get("collection_status") == "ok")
    print(f"  GDELT: {len(gd_records)} records ({ok_count} ok, {len(gd_records) - ok_count} failed, {cached_count} cached)")
    all_gdelt.extend(gd_records)

    # Phase 2: Normalize
    print("\n" + "=" * 60)
    print("Phase 2: Data Normalization")
    print("=" * 60)

    # Use GDELT as both sources (openalex_count will be 0)
    merged = merge_records_by_source([], all_gdelt)
    pivot = create_pivot_table(merged)
    pivot_path = cfg.processed_path / "pivot_table.jsonl"
    save_records_to_jsonl(pivot, pivot_path)
    print(f"  Pivot table: {len(pivot)} rows -> {pivot_path}")

    # Phase 3: Baseline forecast on GDELT counts
    print("\n" + "=" * 60)
    print("Phase 3: Baseline Forecast (GDELT only)")
    print("=" * 60)

    by_topic: dict[str, list[dict]] = {}
    for row in pivot:
        tid = row["topic_id"]
        if tid not in by_topic:
            by_topic[tid] = []
        by_topic[tid].append(row)

    all_results: list[dict] = []
    all_evals: list[dict] = []

    for tid, rows in by_topic.items():
        rows_sorted = sorted(rows, key=lambda r: r["window_start"])
        print(f"\n  [{tid}] {rows_sorted[0]['topic_label']} ({len(rows_sorted)} months)")

        for method in ["moving_average", "linear_regression"]:
            result = forecast_topic(
                pivot_rows=rows_sorted,
                column="gdelt_count",
                method=method,
                train_ratio=cfg.train_ratio,
            )
            ev = evaluate_forecast(result)
            all_results.append(result)
            all_evals.append(ev)
            print(
                f"    gdelt_count          {method:20s} "
                f"MAE={ev['mae']:.2f}  MAPE={ev['mape']:.1f}%  RMSE={ev['rmse']:.2f}"
            )

    # Save results
    results_path = cfg.reports_path / "baseline_results.json"
    evals_path = cfg.reports_path / "baseline_evaluations.json"
    summary = summarize_results(all_evals)

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    with open(evals_path, "w", encoding="utf-8") as f:
        json.dump(all_evals, f, ensure_ascii=False, indent=2)
    with open(cfg.reports_path / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Total evaluations: {summary['total']}")
    print(f"  Average MAE:  {summary['avg_mae']:.2f}")
    print(f"  Average MAPE: {summary['avg_mape']:.1f}%")
    print(f"  Average RMSE: {summary['avg_rmse']:.2f}")

    for method, ms in summary.get("by_method", {}).items():
        print(f"\n  Method: {method}")
        print(f"    avg_mae={ms['avg_mae']:.2f}  avg_mape={ms['avg_mape']:.1f}%  avg_rmse={ms['avg_rmse']:.2f}")

    print(f"\n  Reports saved to: {cfg.reports_path}")
    print("\nGDELT-only test complete.")


if __name__ == "__main__":
    main()
