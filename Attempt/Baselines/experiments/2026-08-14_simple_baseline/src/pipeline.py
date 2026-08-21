"""End-to-end pipeline: collect data → normalize → baseline forecast → evaluate.

Usage:
    python -m Baselines.experiments.2026-08-14_simple_baseline.src.pipeline
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Ensure Shared and local src are importable
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
# New unified collector API (replaces old per-source function clients)
import data_collectors.crossref  # noqa: F401 - registers collector
import data_collectors.gdelt      # noqa: F401 - registers collector
from data_collectors.base import get_collector
from processors.normalize import (
    build_feature_matrix,
    create_pivot_table,
    merge_records_by_source,
    save_records_to_jsonl,
    load_jsonl,
)

from baseline_model import forecast_topic
from evaluator import evaluate_forecast, summarize_results
from report_generator import generate_report


def _load_sources_cfg() -> dict:
    """Load sources.yaml for http settings and per-source config."""
    sources_yaml = ATTEMPT_ROOT / "configs" / "sources.yaml"
    if sources_yaml.exists():
        with open(sources_yaml, "r", encoding="utf-8") as f:
            return _yaml.safe_load(f) or {}
    return {}


def run_collection(cfg: PipelineConfig) -> list[dict]:
    """Phase 1: Collect raw data from CrossRef and GDELT via unified collectors."""
    print("=" * 60)
    print("Phase 1: Data Collection")
    print("=" * 60)

    windows = generate_monthly_windows(cfg.start_date, cfg.end_date)
    print(f"Time windows: {cfg.start_date} → {cfg.end_date} ({len(windows)} months)")

    raw_cfg = _load_sources_cfg()
    http_settings = raw_cfg.get("http", {})
    sources_cfg = raw_cfg.get("sources", {})

    all_crossref: list[dict] = []
    all_gdelt: list[dict] = []

    for source_name, label in [("crossref", "CrossRef"), ("gdelt", "GDELT")]:
        sc = sources_cfg.get(source_name, {})
        if not sc.get("enabled", False):
            print(f"\n  {label}: disabled in sources.yaml, skipping")
            continue
        print(f"\n  {label}: querying {len(windows)} windows x {len(cfg.topics)} topics...")
        collector = get_collector(source_name)
        recs = collector.collect(cfg, http_settings, sc)
        cached_count = sum(1 for r in recs if r.get("cached"))
        ok_count = sum(1 for r in recs if r.get("collection_status") == "ok")
        print(f"    {label}: {len(recs)} records ({ok_count} ok, {len(recs) - ok_count} failed, {cached_count} cached)")
        if source_name == "crossref":
            all_crossref.extend(recs)
        else:
            all_gdelt.extend(recs)

    # Save interim records
    cr_path = cfg.interim_path / "crossref_activity.jsonl"
    gd_path = cfg.interim_path / "gdelt_activity.jsonl"
    save_records_to_jsonl(all_crossref, cr_path)
    save_records_to_jsonl(all_gdelt, gd_path)
    print(f"\n  Saved: {cr_path} ({len(all_crossref)} records)")
    print(f"  Saved: {gd_path} ({len(all_gdelt)} records)")

    return all_crossref + all_gdelt


def run_normalization(
    cfg: PipelineConfig,
    all_records: list[dict] | None = None,
) -> list[dict]:
    """Phase 2: Normalize and create pivot table."""
    print("\n" + "=" * 60)
    print("Phase 2: Data Normalization")
    print("=" * 60)

    if all_records is None:
        cr_records = load_jsonl(cfg.interim_path / "crossref_activity.jsonl")
        gd_records = load_jsonl(cfg.interim_path / "gdelt_activity.jsonl")
        all_records = merge_records_by_source([], gd_records, cr_records)
    else:
        all_records = merge_records_by_source(
            [r for r in all_records if r["source"] == "openalex"],
            [r for r in all_records if r["source"] == "gdelt"],
            [r for r in all_records if r["source"] == "crossref"],
        )

    pivot = create_pivot_table(all_records)
    pivot_path = cfg.processed_path / "pivot_table.jsonl"
    save_records_to_jsonl(pivot, pivot_path)
    print(f"  Pivot table: {len(pivot)} rows → {pivot_path}")

    by_topic = build_feature_matrix(all_records)
    print(f"  Topics in data: {list(by_topic.keys())}")

    return pivot


def run_baseline_forecast(
    cfg: PipelineConfig,
    pivot: list[dict] | None = None,
) -> None:
    """Phase 3: Run baseline forecasts and evaluate."""
    print("\n" + "=" * 60)
    print("Phase 3: Baseline Forecast & Evaluation")
    print("=" * 60)

    if pivot is None:
        pivot = load_jsonl(cfg.processed_path / "pivot_table.jsonl")

    # Group pivot by topic
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

        for column in ["crossref_count", "gdelt_count"]:
            for method in ["moving_average", "linear_regression"]:
                result = forecast_topic(
                    pivot_rows=rows_sorted,
                    column=column,
                    method=method,
                    train_ratio=cfg.train_ratio,
                )
                ev = evaluate_forecast(result)
                all_results.append(result)
                all_evals.append(ev)
                print(
                    f"    {column:20s} {method:20s} "
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
    print(f"    - baseline_results.json")
    print(f"    - baseline_evaluations.json")
    print(f"    - summary.json")


def main() -> None:
    print("Predictive Agents — End-to-End Pipeline")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    cfg = load_pipeline_config()
    ensure_dirs(cfg)

    print(f"Dataset: {cfg.dataset_name}")
    print(f"Topics:  {len(cfg.topics)}")
    print(f"Period:  {cfg.start_date} → {cfg.end_date}")
    print(f"Split:   {cfg.train_ratio}/{cfg.validation_ratio}/{cfg.test_ratio}")

    # Phase 1: Collect
    all_records = run_collection(cfg)

    # Phase 2: Normalize
    pivot = run_normalization(cfg, all_records)

    # Phase 3: Baseline forecast
    run_baseline_forecast(cfg, pivot)

    # Phase 4: AI analysis report (only when data quality is sufficient)
    print("\n" + "=" * 60)
    print("Phase 4: AI Analysis Report")
    print("=" * 60)
    try:
        generate_report(
            reports_path=cfg.reports_path,
            attempt_root=ATTEMPT_ROOT,
        )
    except Exception as e:
        print(f"  Report generation skipped: {e}")

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
