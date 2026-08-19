"""Quick test: generate AI report from existing results without re-running pipeline.

Usage:
    python -m Baselines.experiments.2026-08-14_simple_baseline.src.test_report
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

from config import load_pipeline_config
from report_generator import generate_report


def main() -> None:
    print("Test: AI Report Generation")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    cfg = load_pipeline_config()
    report_path = generate_report(
        reports_path=cfg.reports_path,
        attempt_root=ATTEMPT_ROOT,
    )
    print(f"\nDone! Open the report: {report_path}")


if __name__ == "__main__":
    main()
