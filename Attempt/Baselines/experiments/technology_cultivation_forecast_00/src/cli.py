"""Command-line entry point for the version 00 experiment."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .collectors import collect_crossref, collect_gdelt, collect_openalex, write_records
from .config import load_config
from .scoring import evaluate_ranking, read_records, score_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Technology cultivation forecast 00")
    parser.add_argument("--config", required=True, help="Path to forecast_00.yaml")
    parser.add_argument("--mode", choices=("collect", "score", "backtest"), required=True)
    parser.add_argument("--as-of", default=None, help="Snapshot date in YYYY-MM-DD; defaults to today")
    return parser.parse_args()


def _as_of(value: str | None) -> date:
    return date.fromisoformat(value) if value else date.today()


def _records_path(config: Any) -> Path:
    candidates = sorted(config.paths["interim_dir"].glob("activity_records_00_*.jsonl"))
    if not candidates:
        raise FileNotFoundError("No activity_records_00_*.jsonl found; run collect first")
    return candidates[-1]


def _load_records(config: Any, input_path: Path | None = None, as_of: date | None = None) -> list[dict[str, Any]]:
    if input_path:
        return read_records(input_path)
    pattern = f"activity_records_00_{as_of.isoformat()}_*.jsonl" if as_of else "activity_records_00_*.jsonl"
    records = []
    for path in sorted(config.paths["interim_dir"].glob(pattern)):
        records.extend(read_records(path))
    if not records:
        raise FileNotFoundError(f"No records found for pattern {pattern}; run collect first")
    return records


def collect(config: Any, as_of: date) -> Path:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    outputs = []
    academic_records: list[dict[str, Any]] = []
    # Prefer CrossRef (enabled replacement); fall back to OpenAlex if crossref disabled
    use_crossref = config.raw.get("crossref", {}).get("enabled", False)
    use_openalex = config.raw.get("openalex", {}).get("enabled", True)
    if use_crossref:
        academic_records = collect_crossref(config, as_of)
        output = config.paths["interim_dir"] / f"activity_records_00_{as_of.isoformat()}_crossref.jsonl"
        write_records(academic_records, output)
        outputs.append(str(output))
    if use_openalex:
        openalex_records = collect_openalex(config, as_of)
        output = config.paths["interim_dir"] / f"activity_records_00_{as_of.isoformat()}_openalex.jsonl"
        write_records(openalex_records, output)
        outputs.append(str(output))
        if not academic_records:
            academic_records = openalex_records
    corporate = collect_gdelt(config, as_of)
    output = config.paths["interim_dir"] / f"activity_records_00_{as_of.isoformat()}_gdelt.jsonl"
    write_records(corporate, output)
    outputs.append(str(output))
    failed_corporate = sum(record.get("collection_status") == "failed" for record in corporate)
    failed_academic = sum(record.get("collection_status") == "failed" for record in academic_records)
    print(json.dumps({"outputs": outputs, "academic_records": len(academic_records), "academic_failed": failed_academic, "corporate_records": len(corporate), "corporate_failed": failed_corporate}, ensure_ascii=False, indent=2))
    return Path(outputs[0])


def score(config: Any, input_path: Path | None = None, as_of: date | None = None) -> Path:
    records = _load_records(config, input_path, as_of)
    ranking = score_snapshot(records, config.raw["scoring"])
    snapshot = (as_of or date.today()).isoformat()
    output = config.paths["processed_dir"] / f"forecast_ranking_00_{snapshot}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(ranking, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "topics": len(ranking)}, ensure_ascii=False, indent=2))
    return output


def backtest(config: Any, input_path: Path | None = None, as_of: date | None = None) -> Path:
    records = _load_records(config, input_path, as_of)
    grouped = {}
    for record in records:
        grouped.setdefault(record["window_end"], []).append(record)
    ends = sorted(grouped)
    evaluations = []
    for index in range(2, len(ends) - 1):
        history_end = ends[index]
        history = [record for record in records if record["window_end"] <= history_end]
        future_end = ends[min(index + 2, len(ends) - 1)]
        future_start = date.fromisoformat(history_end) + timedelta(days=1)
        future = [
            record for record in records
            if future_start <= date.fromisoformat(record["window_start"]) <= date.fromisoformat(future_end)
        ]
        predictions = score_snapshot(history, config.raw["scoring"])
        evaluations.append({"history_end": history_end, "future_end": future_end, **evaluate_ranking(predictions, future)})

    snapshot = (as_of or date.today()).isoformat()
    output = config.paths["report_dir"] / f"backtest_00_{snapshot}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evaluations, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "evaluations": len(evaluations)}, ensure_ascii=False, indent=2))
    return output


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if args.mode == "collect":
        collect(config, _as_of(args.as_of))
    elif args.mode == "score":
        score(config, as_of=_as_of(args.as_of) if args.as_of else None)
    else:
        backtest(config, as_of=_as_of(args.as_of) if args.as_of else None)


if __name__ == "__main__":
    main()
