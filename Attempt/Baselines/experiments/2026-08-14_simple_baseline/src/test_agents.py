"""Quick test: run DataCollectionAgent and DataAnalysisAgent.

Usage:
    python -m Baselines.experiments.2026-08-14_simple_baseline.src.test_agents
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
from agents.data_collection_agent import DataCollectionAgent, AgentOptions
from agents.data_analysis_agent import DataAnalysisAgent


def main() -> None:
    print("Test: DataCollectionAgent + DataAnalysisAgent")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    cfg = load_pipeline_config()

    # Phase 1: Collection
    print("=" * 60)
    print("Phase 1: DataCollectionAgent")
    print("=" * 60)
    agent1 = DataCollectionAgent(cfg, AgentOptions(sources_cfg_path=ATTEMPT_ROOT / "configs" / "sources.yaml"))
    res1 = agent1.run()
    print(f"Status: {'OK' if res1.ok else 'FAILED'}")
    print(f"Detail: {res1.detail}")
    print()

    # Phase 2: Analysis
    print("=" * 60)
    print("Phase 2: DataAnalysisAgent")
    print("=" * 60)
    agent2 = DataAnalysisAgent(cfg)
    res2 = agent2.run()
    print(f"Status: {'OK' if res2.ok else 'FAILED'}")
    print(f"Detail: {res2.detail}")
    print()

    print("Done!")


if __name__ == "__main__":
    main()
