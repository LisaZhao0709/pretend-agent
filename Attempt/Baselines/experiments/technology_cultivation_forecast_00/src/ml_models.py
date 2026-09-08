"""GBDT-based forecasting model for technology activity prediction.

Uses GradientBoostingRegressor from scikit-learn to predict future activity
based on historical momentum features from multiple sources (academic, corporate,
community).

Features (per source):
- level: log1p(activity_count) in the latest window
- growth: log1p(latest) - log1p(previous)
- acceleration: growth - previous_growth
- persistence: fraction of recent windows with positive activity

Target:
- Future 30-day total activity (aggregated across all sources)

The model is trained on historical windows and used to rank topics by predicted
future activity. Feature importance is logged for interpretability.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


def _build_features_from_pivot(pivot_records: list[dict[str, Any]]) -> pd.DataFrame:
    """Build feature matrix from pivot table for GBDT training/prediction.

    For each (topic_id, window_start), compute per-source momentum features:
    - level: log1p(activity_count)
    - growth: log1p(current) - log1p(previous)
    - acceleration: growth - previous_growth
    - persistence: fraction of positive activity in recent windows

    Args:
        pivot_records: List of pivot table rows with per-source counts.

    Returns:
        DataFrame with columns: topic_id, window_start, [source]_level,
        [source]_growth, [source]_acceleration, [source]_persistence for each source.
    """
    if not pivot_records:
        return pd.DataFrame()

    df = pd.DataFrame(pivot_records)
    source_cols = [c for c in df.columns if c.endswith("_count")]
    source_names = [c.replace("_count", "") for c in source_cols]

    # Group by topic_id to compute time-series features
    result_rows: list[dict[str, Any]] = []

    for topic_id, group in df.groupby("topic_id"):
        group = group.sort_values("window_start").reset_index(drop=True)

        for i in range(len(group)):
            row = group.iloc[i]
            features: dict[str, Any] = {
                "topic_id": topic_id,
                "window_start": row["window_start"],
            }

            for src in source_names:
                count_col = f"{src}_count"
                current = float(row.get(count_col, 0))

                # level: log1p(current)
                features[f"{src}_level"] = math.log1p(max(current, 0.0))

                # growth: log1p(current) - log1p(previous)
                if i >= 1:
                    prev = float(group.iloc[i - 1].get(count_col, 0))
                    features[f"{src}_growth"] = math.log1p(max(current, 0.0)) - math.log1p(max(prev, 0.0))
                else:
                    features[f"{src}_growth"] = 0.0

                # acceleration: growth - previous_growth
                if i >= 2:
                    prev_prev = float(group.iloc[i - 2].get(count_col, 0))
                    prev_curr = float(group.iloc[i - 1].get(count_col, 0))
                    prev_growth = math.log1p(max(prev_curr, 0.0)) - math.log1p(max(prev_prev, 0.0))
                    current_growth = features[f"{src}_growth"]
                    features[f"{src}_acceleration"] = current_growth - prev_growth
                else:
                    features[f"{src}_acceleration"] = 0.0

                # persistence: fraction of positive activity in recent 3 windows
                start_idx = max(0, i - 2)
                recent_counts = [
                    float(group.iloc[j].get(count_col, 0))
                    for j in range(start_idx, i + 1)
                ]
                if recent_counts:
                    features[f"{src}_persistence"] = sum(1 for c in recent_counts if c > 0) / len(recent_counts)
                else:
                    features[f"{src}_persistence"] = 0.0

            result_rows.append(features)

    return pd.DataFrame(result_rows)


def train_gbdt_model(
    features_df: pd.DataFrame,
    future_activity: dict[str, float],
    params: dict[str, Any] | None = None,
) -> tuple[GradientBoostingRegressor, dict[str, Any]]:
    """Train a GBDT model to predict future activity from momentum features.

    Args:
        features_df: DataFrame with momentum features for each (topic, window).
        future_activity: Dict mapping (topic_id, window_start) to future 30-day activity.
        params: Optional GradientBoostingRegressor hyperparameters.

    Returns:
        Tuple of (trained model, training metadata).
    """
    if params is None:
        params = {
            "n_estimators": 100,
            "learning_rate": 0.1,
            "max_depth": 3,
            "random_state": 42,
        }

    # Align features with future activity targets
    X: list[dict[str, Any]] = []
    y: list[float] = []

    feature_cols = [c for c in features_df.columns if c not in ("topic_id", "window_start")]

    for _, row in features_df.iterrows():
        key = (row["topic_id"], row["window_start"])
        if key in future_activity:
            X.append({col: row[col] for col in feature_cols})
            y.append(future_activity[key])

    if not X:
        raise ValueError("No matching future activity data for training")

    X_df = pd.DataFrame(X)
    y_arr = np.array(y)

    model = GradientBoostingRegressor(**params)
    model.fit(X_df, y_arr)

    # Compute training metrics
    y_pred = model.predict(X_df)
    mae = mean_absolute_error(y_arr, y_pred)
    rmse = math.sqrt(mean_squared_error(y_arr, y_pred))

    metadata = {
        "n_samples": len(X),
        "n_features": len(feature_cols),
        "feature_names": feature_cols,
        "feature_importance": dict(zip(feature_cols, model.feature_importances_.tolist())),
        "params": params,
        "training_mae": mae,
        "training_rmse": rmse,
    }

    return model, metadata


def predict_gbdt_score(
    model: GradientBoostingRegressor,
    features_df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Predict future activity scores for the latest window of each topic.

    Args:
        model: Trained GradientBoostingRegressor.
        features_df: DataFrame with momentum features.

    Returns:
        List of dicts with topic_id, predicted_score, feature_values.
    """
    # Get the latest window for each topic
    latest_idx = features_df.groupby("topic_id")["window_start"].idxmax()
    latest_features = features_df.loc[latest_idx].reset_index(drop=True)

    feature_cols = [c for c in latest_features.columns if c not in ("topic_id", "window_start")]
    X = latest_features[feature_cols]

    scores = model.predict(X)

    results: list[dict[str, Any]] = []
    for i, row in latest_features.iterrows():
        results.append({
            "topic_id": row["topic_id"],
            "window_start": row["window_start"],
            "predicted_score": float(scores[i]),
            "features": {col: float(row[col]) for col in feature_cols},
        })

    return results


def save_model(model: GradientBoostingRegressor, metadata: dict[str, Any], path: Path) -> None:
    """Save the trained model and metadata to disk.

    Args:
        model: Trained GradientBoostingRegressor.
        metadata: Training metadata.
        path: Directory to save model files.
    """
    path.mkdir(parents=True, exist_ok=True)

    import joblib
    joblib.dump(model, path / "gbdt_model.joblib")

    with open(path / "gbdt_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def load_model(path: Path) -> tuple[GradientBoostingRegressor, dict[str, Any]]:
    """Load a trained model and metadata from disk.

    Args:
        path: Directory containing model files.

    Returns:
        Tuple of (model, metadata).
    """
    import joblib
    model = joblib.load(path / "gbdt_model.joblib")

    with open(path / "gbdt_metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return model, metadata
