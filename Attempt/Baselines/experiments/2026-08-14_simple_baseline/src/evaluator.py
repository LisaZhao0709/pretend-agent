"""Evaluation metrics for forecasting results."""

from __future__ import annotations

import numpy as np
from typing import Any


def mean_absolute_error(actuals: list[float], predictions: list[float]) -> float:
    """Calculate MAE.

    Args:
        actuals: Ground truth values.
        predictions: Forecasted values.

    Returns:
        Mean absolute error.
    """
    if len(actuals) == 0:
        return 0.0
    return float(np.mean(np.abs(np.array(actuals) - np.array(predictions))))


def mean_absolute_percentage_error(
    actuals: list[float],
    predictions: list[float],
) -> float:
    """Calculate MAPE.

    Args:
        actuals: Ground truth values.
        predictions: Forecasted values.

    Returns:
        Mean absolute percentage error (0-100 scale).
    """
    if len(actuals) == 0:
        return 0.0
    actuals_arr = np.array(actuals, dtype=float)
    preds_arr = np.array(predictions, dtype=float)
    mask = actuals_arr != 0
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs((actuals_arr[mask] - preds_arr[mask]) / actuals_arr[mask])) * 100)


def root_mean_squared_error(actuals: list[float], predictions: list[float]) -> float:
    """Calculate RMSE.

    Args:
        actuals: Ground truth values.
        predictions: Forecasted values.

    Returns:
        Root mean squared error.
    """
    if len(actuals) == 0:
        return 0.0
    return float(np.sqrt(np.mean((np.array(actuals) - np.array(predictions)) ** 2)))


def evaluate_forecast(result: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a forecast result dict with MAE, MAPE, and RMSE.

    Args:
        result: Output from baseline_model.forecast_topic.

    Returns:
        Dict with topic_id, method, mae, mape, rmse, test_size.
    """
    actuals = result["actuals"]
    predictions = result["predictions"]

    return {
        "topic_id": result["topic_id"],
        "topic_label": result["topic_label"],
        "column": result["column"],
        "method": result["method"],
        "mae": mean_absolute_error(actuals, predictions),
        "mape": mean_absolute_percentage_error(actuals, predictions),
        "rmse": root_mean_squared_error(actuals, predictions),
        "test_size": result["test_size"],
    }


def summarize_results(
    evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate evaluation metrics across all topics and methods.

    Args:
        evaluations: List of evaluation dicts.

    Returns:
        Summary dict with average and per-method metrics.
    """
    if not evaluations:
        return {"total": 0, "avg_mae": 0, "avg_mape": 0, "avg_rmse": 0}

    by_method: dict[str, list[dict[str, Any]]] = {}
    for ev in evaluations:
        method = ev["method"]
        if method not in by_method:
            by_method[method] = []
        by_method[method].append(ev)

    method_summary: dict[str, dict[str, float]] = {}
    for method, evs in by_method.items():
        method_summary[method] = {
            "avg_mae": float(np.mean([e["mae"] for e in evs])),
            "avg_mape": float(np.mean([e["mape"] for e in evs])),
            "avg_rmse": float(np.mean([e["rmse"] for e in evs])),
            "count": len(evs),
        }

    return {
        "total": len(evaluations),
        "avg_mae": float(np.mean([e["mae"] for e in evaluations])),
        "avg_mape": float(np.mean([e["mape"] for e in evaluations])),
        "avg_rmse": float(np.mean([e["rmse"] for e in evaluations])),
        "by_method": method_summary,
    }
