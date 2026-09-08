"""Tests for GBDT-based forecasting model.

Run from Baselines/experiments/technology_cultivation_forecast_00/ with:
    python -m pytest tests/test_ml_models.py -v
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to path
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from ml_models import (
    _build_features_from_pivot,
    train_gbdt_model,
    predict_gbdt_score,
    save_model,
    load_model,
)


# ---------------------------------------------------------------------------
# Unit tests: feature building
# ---------------------------------------------------------------------------

def test_build_features_from_pivot() -> None:
    """Should build momentum features from pivot table."""
    pivot_records = [
        {
            "topic_id": "ai",
            "topic_label": "AI",
            "window_start": "2026-01",
            "window_end": "2026-01",
            "crossref_count": 10,
            "gdelt_count": 100,
            "github_count": 5,
        },
        {
            "topic_id": "ai",
            "topic_label": "AI",
            "window_start": "2026-02",
            "window_end": "2026-02",
            "crossref_count": 20,
            "gdelt_count": 110,
            "github_count": 10,
        },
        {
            "topic_id": "ai",
            "topic_label": "AI",
            "window_start": "2026-03",
            "window_end": "2026-03",
            "crossref_count": 15,
            "gdelt_count": 105,
            "github_count": 8,
        },
    ]

    start = time.perf_counter()
    df = _build_features_from_pivot(pivot_records)
    duration = (time.perf_counter() - start) * 1000

    print(f"  [SUCCESS] _build_features_from_pivot | 耗时: {duration:.2f}ms")
    print(f"  输入: 3 pivot rows for topic 'ai'")
    print(f"  输出 shape: {df.shape}")
    print(f"  列: {list(df.columns)}")

    assert len(df) == 3
    assert "topic_id" in df.columns
    assert "window_start" in df.columns
    assert "crossref_level" in df.columns
    assert "crossref_growth" in df.columns
    assert "crossref_acceleration" in df.columns
    assert "crossref_persistence" in df.columns


def test_build_features_empty() -> None:
    """Should return empty DataFrame for empty input."""
    df = _build_features_from_pivot([])
    assert len(df) == 0


# ---------------------------------------------------------------------------
# Unit tests: model training and prediction
# ---------------------------------------------------------------------------

def test_train_gbdt_model() -> None:
    """Should train a GBDT model and return metadata."""
    # Mock features and future activity
    features_df = _build_features_from_pivot([
        {
            "topic_id": "ai",
            "topic_label": "AI",
            "window_start": "2026-01",
            "crossref_count": 10,
            "gdelt_count": 100,
            "github_count": 5,
        },
        {
            "topic_id": "ai",
            "topic_label": "AI",
            "window_start": "2026-02",
            "crossref_count": 20,
            "gdelt_count": 110,
            "github_count": 10,
        },
    ])
    future_activity = {
        ("ai", "2026-01"): 150,
        ("ai", "2026-02"): 180,
    }

    start = time.perf_counter()
    model, metadata = train_gbdt_model(features_df, future_activity)
    duration = (time.perf_counter() - start) * 1000

    print(f"  [SUCCESS] train_gbdt_model | 耗时: {duration:.2f}ms")
    print(f"  训练样本数: {metadata['n_samples']}")
    print(f"  特征数: {metadata['n_features']}")
    print(f"  训练 MAE: {metadata['training_mae']:.2f}")
    print(f"  训练 RMSE: {metadata['training_rmse']:.2f}")

    assert metadata["n_samples"] == 2
    assert metadata["n_features"] > 0
    assert "feature_importance" in metadata
    assert metadata["training_mae"] >= 0


def test_predict_gbdt_score() -> None:
    """Should predict scores for the latest window of each topic."""
    features_df = _build_features_from_pivot([
        {
            "topic_id": "ai",
            "topic_label": "AI",
            "window_start": "2026-01",
            "crossref_count": 10,
            "gdelt_count": 100,
            "github_count": 5,
        },
        {
            "topic_id": "ai",
            "topic_label": "AI",
            "window_start": "2026-02",
            "crossref_count": 20,
            "gdelt_count": 110,
            "github_count": 10,
        },
        {
            "topic_id": "robotics",
            "topic_label": "Robotics",
            "window_start": "2026-01",
            "crossref_count": 5,
            "gdelt_count": 50,
            "github_count": 3,
        },
        {
            "topic_id": "robotics",
            "topic_label": "Robotics",
            "window_start": "2026-02",
            "crossref_count": 8,
            "gdelt_count": 60,
            "github_count": 4,
        },
    ])
    future_activity = {
        ("ai", "2026-01"): 150,
        ("ai", "2026-02"): 180,
        ("robotics", "2026-01"): 80,
        ("robotics", "2026-02"): 100,
    }

    model, _ = train_gbdt_model(features_df, future_activity)

    start = time.perf_counter()
    predictions = predict_gbdt_score(model, features_df)
    duration = (time.perf_counter() - start) * 1000

    print(f"  [SUCCESS] predict_gbdt_score | 耗时: {duration:.2f}ms")
    print(f"  预测数: {len(predictions)}")
    for pred in predictions:
        print(f"  {pred['topic_id']}: {pred['predicted_score']:.2f}")

    assert len(predictions) == 2  # One per topic (latest window)
    assert all("topic_id" in p for p in predictions)
    assert all("predicted_score" in p for p in predictions)
    assert all("features" in p for p in predictions)


# ---------------------------------------------------------------------------
# Integration tests: model save/load
# ---------------------------------------------------------------------------

def test_save_and_load_model(tmp_path: Path) -> None:
    """Should save and load a trained model with metadata."""
    features_df = _build_features_from_pivot([
        {
            "topic_id": "ai",
            "topic_label": "AI",
            "window_start": "2026-01",
            "crossref_count": 10,
            "gdelt_count": 100,
            "github_count": 5,
        },
    ])
    future_activity = {("ai", "2026-01"): 150}

    model, metadata = train_gbdt_model(features_df, future_activity)
    model_dir = tmp_path / "gbdt_model"

    start = time.perf_counter()
    save_model(model, metadata, model_dir)
    duration = (time.perf_counter() - start) * 1000

    print(f"  [SUCCESS] save_model | 耗时: {duration:.2f}ms")
    print(f"  保存路径: {model_dir}")

    assert (model_dir / "gbdt_model.joblib").exists()
    assert (model_dir / "gbdt_metadata.json").exists()

    # Load and verify
    start = time.perf_counter()
    loaded_model, loaded_metadata = load_model(model_dir)
    duration = (time.perf_counter() - start) * 1000

    print(f"  [SUCCESS] load_model | 耗时: {duration:.2f}ms")
    print(f"  加载的元数据样本数: {loaded_metadata['n_samples']}")

    assert loaded_metadata["n_samples"] == metadata["n_samples"]
    assert loaded_metadata["n_features"] == metadata["n_features"]
