"""Simple baseline forecasting models: moving average and linear regression."""

from __future__ import annotations

import numpy as np
from typing import Any


def moving_average_forecast(
    history: list[float],
    window: int = 3,
) -> float:
    """Forecast next value using simple moving average.

    Args:
        history: List of historical values (chronological order).
        window: Number of recent values to average.

    Returns:
        Forecasted next value.
    """
    if len(history) == 0:
        return 0.0
    if len(history) < window:
        return float(np.mean(history))
    return float(np.mean(history[-window:]))


def linear_regression_forecast(
    history: list[float],
) -> float:
    """Forecast next value using linear regression on time index.

    Args:
        history: List of historical values (chronological order).

    Returns:
        Forecasted next value (clipped to >= 0).
    """
    n = len(history)
    if n == 0:
        return 0.0
    if n == 1:
        return history[0]

    x = np.arange(n)
    y = np.array(history, dtype=float)
    coeffs = np.polyfit(x, y, 1)
    next_x = n
    forecast = coeffs[0] * next_x + coeffs[1]
    return max(0.0, float(forecast))


def forecast_topic(
    pivot_rows: list[dict[str, Any]],
    column: str = "openalex_count",
    method: str = "moving_average",
    window: int = 3,
    train_ratio: float = 0.7,
) -> dict[str, Any]:
    """Run backtest forecast for a single topic.

    Splits data into train/test by time, then iteratively forecasts
    each test point using only past data.

    Args:
        pivot_rows: List of pivot table rows for one topic.
        column: Which count column to predict ("openalex_count" or "gdelt_count").
        method: "moving_average" or "linear_regression".
        window: Window size for moving average.
        train_ratio: Fraction of data used as initial training set.

    Returns:
        Dict with topic_id, method, predictions, actuals, windows.
    """
    values = [row[column] for row in pivot_rows]
    windows = [row["window_start"] for row in pivot_rows]
    n = len(values)
    split_idx = max(1, int(n * train_ratio))

    train = values[:split_idx]
    test = values[split_idx:]
    test_windows = windows[split_idx:]

    predictions: list[float] = []
    actuals: list[float] = []
    history = list(train)

    for i, actual in enumerate(test):
        if method == "moving_average":
            pred = moving_average_forecast(history, window=window)
        elif method == "linear_regression":
            pred = linear_regression_forecast(history)
        else:
            raise ValueError(f"Unknown method: {method}")

        predictions.append(pred)
        actuals.append(actual)
        history.append(actual)

    return {
        "topic_id": pivot_rows[0]["topic_id"],
        "topic_label": pivot_rows[0]["topic_label"],
        "column": column,
        "method": method,
        "train_size": split_idx,
        "test_size": len(test),
        "test_windows": test_windows,
        "predictions": predictions,
        "actuals": actuals,
    }
