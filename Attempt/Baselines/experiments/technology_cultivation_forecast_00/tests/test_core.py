from __future__ import annotations

from pathlib import Path

from src.config import load_config
from src.http_client import PoliteApiClient
from src.scoring import evaluate_ranking, score_snapshot


def test_config_loads() -> None:
    config = load_config(Path(__file__).parents[1] / "configs" / "forecast_00.yaml")
    assert config.raw["version"] == "00"
    assert len(config.topics) == 6


def test_cache_name_is_stable(tmp_path: Path) -> None:
    settings = {
        "user_agent": "test",
        "contact_email_env": "MISSING_CONTACT_EMAIL",
        "timeout_seconds": 1,
        "max_retries": 0,
        "min_interval_seconds": 0,
        "backoff_factor_seconds": 0,
        "max_backoff_seconds": 0,
        "jitter_seconds": 0,
        "respect_retry_after": True,
    }
    client = PoliteApiClient(tmp_path, settings)
    first = client._cache_name("https://example.com", {"b": 2, "a": 1}, "x")
    second = client._cache_name("https://example.com", {"a": 1, "b": 2}, "x")
    assert first == second


def test_score_and_evaluate() -> None:
    records = []
    for source in ("crossref", "gdelt"):
        for topic_id, values in (("rising", [1, 2, 4, 8]), ("flat", [4, 4, 4, 4])):
            for index, value in enumerate(values):
                records.append(
                    {
                        "source": source,
                        "topic_id": topic_id,
                        "topic_label": topic_id,
                        "window_start": f"2026-01-{index * 15 + 1:02d}",
                        "window_end": f"2026-01-{index * 15 + 15:02d}",
                        "activity_count": value,
                    }
                )
    scoring = {
        "academic_weight": 0.5,
        "corporate_weight": 0.5,
        "growth_weight": 0.45,
        "acceleration_weight": 0.25,
        "persistence_weight": 0.20,
        "level_weight": 0.10,
    }
    ranking = score_snapshot(records, scoring)
    assert ranking[0]["topic_id"] == "rising"
    assert ranking[0]["data_status"] == "complete"
    evaluation = evaluate_ranking(ranking, [
        {"source": "crossref", "topic_id": "rising", "activity_count": 10},
        {"source": "gdelt", "topic_id": "rising", "activity_count": 10},
        {"source": "crossref", "topic_id": "flat", "activity_count": 1},
        {"source": "gdelt", "topic_id": "flat", "activity_count": 1},
    ])
    assert evaluation["top1_topic_id"] == "rising"
    assert evaluation["top1_lift"] > 1


def test_partial_source_does_not_create_joint_score() -> None:
    records = []
    for topic_id, values in (("rising", [1, 2, 4]), ("flat", [4, 4, 4])):
        for index, value in enumerate(values):
            records.append(
                {
                    "source": "crossref",
                    "topic_id": topic_id,
                    "topic_label": topic_id,
                    "window_start": f"2026-01-{index * 15 + 1:02d}",
                    "window_end": f"2026-01-{index * 15 + 15:02d}",
                    "activity_count": value,
                }
            )
    scoring = {
        "academic_weight": 0.5,
        "corporate_weight": 0.5,
        "growth_weight": 0.45,
        "acceleration_weight": 0.25,
        "persistence_weight": 0.20,
        "level_weight": 0.10,
    }
    ranking = score_snapshot(records, scoring)
    assert all(item["data_status"] == "partial" for item in ranking)
    assert all(item["joint_score"] is None for item in ranking)
