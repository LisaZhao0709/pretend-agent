"""Transparent momentum scoring and rolling evaluation."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable


def read_records(path: str | Path) -> list[dict[str, Any]]:
    """Read newline-delimited JSON records."""

    with Path(path).open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _safe_growth(current: float, previous: float) -> float:
    """Return a bounded log growth signal."""

    return math.log1p(max(current, 0.0)) - math.log1p(max(previous, 0.0))


def _normalize(values: dict[str, float]) -> dict[str, float]:
    """Min-max normalize values; return 0.5 for a constant series."""

    if not values:
        return {}
    low, high = min(values.values()), max(values.values())
    if math.isclose(low, high):
        return {key: 0.5 for key in values}
    return {key: (value - low) / (high - low) for key, value in values.items()}


def score_snapshot(records: Iterable[dict[str, Any]], scoring_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Score the latest window for every source and topic."""

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        if record.get("collection_status", "ok") != "ok" or record.get("activity_count") is None:
            continue
        key = (record["source"], record["topic_id"])
        grouped.setdefault(key, []).append(record)

    raw_features: list[dict[str, Any]] = []
    for (source, topic_id), items in grouped.items():
        ordered = sorted(items, key=lambda item: item["window_end"])
        if len(ordered) < 3:
            continue
        values = [float(item["activity_count"]) for item in ordered]
        latest, previous, before_previous = values[-1], values[-2], values[-3]
        growth = _safe_growth(latest, previous)
        previous_growth = _safe_growth(previous, before_previous)
        acceleration = growth - previous_growth
        persistence = sum(value > 0 for value in values[-3:]) / 3
        raw_features.append(
            {
                "source": source,
                "topic_id": topic_id,
                "topic_label": ordered[-1]["topic_label"],
                "window_start": ordered[-1]["window_start"],
                "window_end": ordered[-1]["window_end"],
                "latest_activity": latest,
                "growth": growth,
                "acceleration": acceleration,
                "persistence": persistence,
            }
        )

    by_source: dict[str, list[dict[str, Any]]] = {}
    for feature in raw_features:
        by_source.setdefault(feature["source"], []).append(feature)
    for source, features in by_source.items():
        normalized = {
            key: _normalize({item["topic_id"]: float(item[key]) for item in features})
            for key in ("latest_activity", "growth", "acceleration", "persistence")
        }
        feature_weights = {
            "latest_activity": float(scoring_config["level_weight"]),
            "growth": float(scoring_config["growth_weight"]),
            "acceleration": float(scoring_config["acceleration_weight"]),
            "persistence": float(scoring_config["persistence_weight"]),
        }
        weight_total = sum(feature_weights.values())
        if weight_total <= 0:
            raise ValueError("Feature weights must sum to a positive value")
        for item in features:
            item["source_score"] = sum(
                feature_weights[key] * normalized[key][item["topic_id"]]
                for key in feature_weights
            ) / weight_total

    combined: dict[str, dict[str, Any]] = {}
    for feature in raw_features:
        item = combined.setdefault(feature["topic_id"], {"topic_id": feature["topic_id"], "topic_label": feature["topic_label"]})
        item[f"{feature['source']}_score"] = feature["source_score"]
        item[f"{feature['source']}_features"] = feature

    output: list[dict[str, Any]] = []
    academic_weight = float(scoring_config["academic_weight"])
    corporate_weight = float(scoring_config["corporate_weight"])
    weight_total = academic_weight + corporate_weight
    for item in combined.values():
        # Prefer crossref_score (enabled replacement); fall back to openalex_score
        academic = 0.0
        has_academic = False
        if "crossref_score" in item:
            academic = max(float(item["crossref_score"]), 0.0)
            has_academic = True
        elif "openalex_score" in item:
            academic = max(float(item["openalex_score"]), 0.0)
            has_academic = True
        corporate = max(float(item.get("gdelt_score", 0.0)), 0.0)
        has_corporate = "gdelt_score" in item
        if has_academic and has_corporate:
            if academic > 0 and corporate > 0:
                joint = math.exp((academic_weight * math.log(academic) + corporate_weight * math.log(corporate)) / weight_total)
            else:
                joint = 0.0
        else:
            joint = None
        output.append({
            **item,
            "data_status": "complete" if has_academic and has_corporate else "partial",
            "joint_score": joint,
        })
    return sorted(output, key=lambda item: item["joint_score"] if item["joint_score"] is not None else -1.0, reverse=True)


def evaluate_ranking(predictions: list[dict[str, Any]], future_records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate whether predicted topics had higher future activity."""

    source_topic_activity: dict[tuple[str, str], float] = {}
    for record in future_records:
        if record.get("collection_status", "ok") != "ok" or record.get("activity_count") is None:
            continue
        key = (record["source"], record["topic_id"])
        source_topic_activity[key] = source_topic_activity.get(key, 0.0) + float(record["activity_count"])
    by_source: dict[str, dict[str, float]] = {}
    for (source, topic_id), activity in source_topic_activity.items():
        by_source.setdefault(source, {})[topic_id] = math.log1p(max(activity, 0.0))
    normalized_by_source = {source: _normalize(values) for source, values in by_source.items()}
    future_by_topic: dict[str, float] = {}
    topic_ids = {topic_id for _, topic_id in source_topic_activity}
    for topic_id in topic_ids:
        values = [normalized[topic_id] for normalized in normalized_by_source.values() if topic_id in normalized]
        future_by_topic[topic_id] = sum(values) / len(values) if values else 0.0

    ranked = [item for item in predictions if item.get("joint_score") is not None and item["topic_id"] in future_by_topic]
    if not ranked:
        return {"status": "insufficient_complete_sources", "evaluated_topics": 0, "top1_future_activity": None, "mean_future_activity": None}
    top1 = future_by_topic[ranked[0]["topic_id"]]
    mean_activity = sum(future_by_topic[item["topic_id"]] for item in ranked) / len(ranked)
    return {
        "status": "ok",
        "evaluated_topics": len(ranked),
        "top1_topic_id": ranked[0]["topic_id"],
        "top1_future_activity": top1,
        "mean_future_activity": mean_activity,
        "top1_lift": top1 / mean_activity if mean_activity else None,
    }
