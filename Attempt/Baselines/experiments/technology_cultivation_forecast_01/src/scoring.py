import math
import statistics
from typing import Any, Iterable

def _safe_growth(current: float, previous: float) -> float:
    return math.log1p(max(current, 0.0)) - math.log1p(max(previous, 0.0))

def _calculate_ema(series: list[float], span: int) -> float:
    if not series:
        return 0.0
    alpha = 2.0 / (span + 1.0)
    ema = series[0]
    for val in series[1:]:
        ema = (val * alpha) + (ema * (1.0 - alpha))
    return ema

def _robust_normalize(values: dict[str, float]) -> dict[str, float]:
    """Robust normalization using median and IQR, scaled to [0, 1]."""
    if not values:
        return {}
    vals = list(values.values())
    if len(vals) < 2:
        return {k: 0.5 for k in values}
    
    vals.sort()
    q1_idx = len(vals) // 4
    q3_idx = (len(vals) * 3) // 4
    q1 = vals[q1_idx]
    q3 = vals[q3_idx]
    iqr = q3 - q1
    
    # If IQR is 0, fallback to min-max, or 0.5 if all equal
    if math.isclose(iqr, 0.0):
        low, high = vals[0], vals[-1]
        if math.isclose(low, high):
            return {k: 0.5 for k in values}
        return {k: (v - low) / (high - low) for k, v in values.items()}
    
    # Sigmoid scaling around median
    median = vals[len(vals) // 2]
    result = {}
    for k, v in values.items():
        # z-score equivalent using IQR: z = (x - median) / (IQR / 1.35)
        # 1.35 is roughly IQR of standard normal
        z = (v - median) / (iqr / 1.34896)
        # sigmoid to bind to [0, 1]
        result[k] = 1.0 / (1.0 + math.exp(-z))
    return result

def _aggregate_github_to_monthly(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_month: dict[str, dict[str, Any]] = {}
    for rec in records:
        day_str = rec.get("window_start", "")
        if len(day_str) >= 7:
            month = day_str[:7]
        else:
            continue
        existing = by_month.get(month)
        if existing is None or day_str > existing.get("window_start", ""):
            by_month[month] = {
                **rec,
                "window_start": month,
                "window_end": month,
            }
    return sorted(by_month.values(), key=lambda r: r["window_start"])

def score_snapshot(records: Iterable[dict[str, Any]], scoring_config: dict[str, Any], sources_config: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    raw_records = list(records)
    github_daily: list[dict[str, Any]] = []
    other_records: list[dict[str, Any]] = []
    for rec in raw_records:
        if rec.get("collection_status", "ok") != "ok" or rec.get("activity_count") is None:
            continue
        if rec.get("source") == "github":
            github_daily.append(rec)
        else:
            other_records.append(rec)

    github_monthly = _aggregate_github_to_monthly(github_daily)

    all_records = other_records + github_monthly

    # Calculate total activity per (source, window_end) for relative topic share
    window_totals: dict[tuple[str, str], float] = {}
    for r in all_records:
        w_key = (r["source"], r["window_end"])
        window_totals[w_key] = window_totals.get(w_key, 0.0) + float(r["activity_count"])

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in all_records:
        key = (record["source"], record["topic_id"])
        grouped.setdefault(key, []).append(record)

    raw_features: list[dict[str, Any]] = []
    for (source, topic_id), items in grouped.items():
        ordered = sorted(items, key=lambda item: item["window_end"])
        if len(ordered) < 3:
            continue
        values = [float(item["activity_count"]) for item in ordered]
        
        # Relative topic share across time
        share_values = []
        for item in ordered:
            tot = window_totals.get((source, item["window_end"]), 0.0)
            share = (float(item["activity_count"]) + 1.0) / (tot + 6.0) if tot > 0 else 0.0
            share_values.append(share)

        # EMA on absolute values
        ema_short = _calculate_ema(values, span=3)
        ema_long = _calculate_ema(values, span=6)
        macd = ema_short - ema_long

        # Relative share momentum (EMA on share)
        share_ema_short = _calculate_ema(share_values, span=3)
        share_ema_long = _calculate_ema(share_values, span=6)
        share_macd = share_ema_short - share_ema_long
        relative_growth = (share_macd / (share_ema_long + 1e-6)) if share_ema_long > 0 else 0.0
        
        # Volatility (stdev of log growth)
        growths = [_safe_growth(values[i], values[i-1]) for i in range(1, len(values))]
        volatility = statistics.stdev(growths) if len(growths) > 1 else 0.0
        
        # Persistence (ratio of months with positive activity over last 12 months)
        recent_values = values[-12:]
        persistence = sum(v > 0 for v in recent_values) / len(recent_values)
        
        raw_features.append(
            {
                "source": source,
                "topic_id": topic_id,
                "topic_label": ordered[-1]["topic_label"],
                "window_start": ordered[-1]["window_start"],
                "window_end": ordered[-1]["window_end"],
                "latest_activity": values[-1],
                "latest_share": round(share_values[-1], 4),
                "ema_short": ema_short,
                "macd": macd,
                "relative_growth": relative_growth,
                "volatility": volatility,
                "persistence": persistence,
            }
        )

    by_source: dict[str, list[dict[str, Any]]] = {}
    for feature in raw_features:
        by_source.setdefault(feature["source"], []).append(feature)
        
    for source, features in by_source.items():
        normalized = {
            "ema_short": _robust_normalize({item["topic_id"]: float(item["ema_short"]) for item in features}),
            "macd": _robust_normalize({item["topic_id"]: float(item["macd"]) for item in features}),
            "relative_growth": _robust_normalize({item["topic_id"]: float(item["relative_growth"]) for item in features}),
            "stability": _robust_normalize({item["topic_id"]: -float(item["volatility"]) for item in features}),
            "persistence": _robust_normalize({item["topic_id"]: float(item["persistence"]) for item in features}),
        }
        
        feature_weights = {
            "ema_short": float(scoring_config.get("ema_short_weight", 0.25)),
            "macd": float(scoring_config.get("macd_weight", 0.3)),
            "relative_growth": float(scoring_config.get("relative_growth_weight", 0.2)),
            "stability": float(scoring_config.get("stability_weight", 0.125)),
            "persistence": float(scoring_config.get("persistence_weight", 0.125)),
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
    
    dimension_sources: dict[str, list[str]] = {}
    if sources_config:
        for src, cfg in sources_config.items():
            dim = cfg.get("dimension")
            if dim:
                dimension_sources.setdefault(dim, []).append(src)
    else:
        dimension_sources = {
            "academic": ["crossref", "openalex", "arxiv", "uspto"],
            "corporate": ["gdelt"],
            "community": ["github"]
        }
        
    weight_total = sum(float(scoring_config.get(f"{dim}_weight", 0.0)) for dim in dimension_sources)
    if weight_total <= 0:
        raise ValueError("Scoring weights must sum to a positive value")

    for item in combined.values():
        dimension_scores = {}
        for dim, srcs in dimension_sources.items():
            scores = []
            for src in srcs:
                key = f"{src}_score"
                if key in item:
                    scores.append(max(float(item[key]), 0.0))
            if scores:
                dimension_scores[dim] = sum(scores) / len(scores)

        components: list[tuple[float, float]] = []
        for dim, val in dimension_scores.items():
            weight = float(scoring_config.get(f"{dim}_weight", 0.0))
            if weight > 0:
                components.append((val, weight))

        if len(components) >= 2:
            log_sum = 0.0
            w_sum = 0.0
            for value, weight in components:
                if value > 0:
                    log_sum += weight * math.log(value)
                    w_sum += weight
            joint = math.exp(log_sum / w_sum) if w_sum > 0 else 0.0
        elif len(components) == 1:
            joint = components[0][0]
        else:
            joint = None

        source_count = len(dimension_scores)
        output.append({
            **item,
            "data_status": "complete" if source_count >= 3 else ("partial" if source_count >= 1 else "empty"),
            "joint_score": joint,
        })
    return sorted(output, key=lambda item: item["joint_score"] if item["joint_score"] is not None else -1.0, reverse=True)

def evaluate_ranking(predictions: list[dict[str, Any]], future_records: Iterable[dict[str, Any]], sources_config: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    raw_future = list(future_records)
    github_daily_future: list[dict[str, Any]] = []
    other_future: list[dict[str, Any]] = []
    for rec in raw_future:
        if rec.get("collection_status", "ok") != "ok" or rec.get("activity_count") is None:
            continue
        if rec.get("source") == "github":
            github_daily_future.append(rec)
        else:
            other_future.append(rec)
    github_monthly_future = _aggregate_github_to_monthly(github_daily_future)
    all_future = other_future + github_monthly_future

    src_to_dim: dict[str, str] = {}
    if sources_config:
        for src, cfg in sources_config.items():
            dim = cfg.get("dimension")
            if dim:
                src_to_dim[src] = dim
    else:
        src_to_dim = {
            "crossref": "academic",
            "openalex": "academic",
            "arxiv": "academic",
            "uspto": "academic",
            "gdelt": "corporate",
            "github": "community"
        }
    
    dimension_future: list[dict[str, Any]] = []
    for rec in all_future:
        src = rec.get("source", "")
        dim = src_to_dim.get(src, src)
        dimension_future.append({**rec, "source": dim})
    all_future = dimension_future

    source_topic_activity: dict[tuple[str, str], float] = {}
    for record in all_future:
        key = (record["source"], record["topic_id"])
        source_topic_activity[key] = source_topic_activity.get(key, 0.0) + float(record["activity_count"])
    by_source: dict[str, dict[str, float]] = {}
    for (source, topic_id), activity in source_topic_activity.items():
        by_source.setdefault(source, {})[topic_id] = math.log1p(max(activity, 0.0))
    normalized_by_source = {source: _robust_normalize(values) for source, values in by_source.items()}
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
    
    # Calculate ranking metrics
    ranked_topic_ids = [item["topic_id"] for item in ranked]
    pred_scores_dict = {item["topic_id"]: float(item.get("joint_score") or 0.0) for item in ranked}
    
    spearman_rho = calculate_spearman_rho(pred_scores_dict, future_by_topic)
    ndcg_3 = calculate_ndcg_at_k(ranked_topic_ids, future_by_topic, k=3)
    ndcg_5 = calculate_ndcg_at_k(ranked_topic_ids, future_by_topic, k=5)

    return {
        "status": "ok",
        "evaluated_topics": len(ranked),
        "top1_topic_id": ranked[0]["topic_id"],
        "top1_future_activity": round(top1, 4),
        "mean_future_activity": round(mean_activity, 4),
        "top1_lift": round(top1 / mean_activity, 4) if mean_activity else None,
        "spearman_rho": spearman_rho,
        "ndcg@3": ndcg_3,
        "ndcg@5": ndcg_5,
    }


def calculate_spearman_rho(pred_scores: dict[str, float], true_scores: dict[str, float]) -> float:
    """Calculate Spearman rank correlation coefficient between prediction and true ranking."""
    common_topics = [t for t in pred_scores if t in true_scores]
    n = len(common_topics)
    if n < 2:
        return 0.0

    sorted_pred = sorted(common_topics, key=lambda t: pred_scores[t], reverse=True)
    pred_ranks = {t: rank for rank, t in enumerate(sorted_pred, start=1)}

    sorted_true = sorted(common_topics, key=lambda t: true_scores[t], reverse=True)
    true_ranks = {t: rank for rank, t in enumerate(sorted_true, start=1)}

    d_sq_sum = sum((pred_ranks[t] - true_ranks[t]) ** 2 for t in common_topics)
    rho = 1.0 - (6.0 * d_sq_sum) / (n * (n**2 - 1))
    return round(rho, 4)


def calculate_ndcg_at_k(ranked_topic_ids: list[str], true_relevance: dict[str, float], k: int = 3) -> float:
    """Calculate Normalized Discounted Cumulative Gain at K (NDCG@K)."""
    if not ranked_topic_ids or not true_relevance:
        return 0.0

    k = min(k, len(ranked_topic_ids))
    dcg = 0.0
    for i in range(k):
        topic = ranked_topic_ids[i]
        rel = max(true_relevance.get(topic, 0.0), 0.0)
        dcg += (2.0 ** rel - 1.0) / math.log2(i + 2)

    ideal_topics = sorted(true_relevance.keys(), key=lambda t: true_relevance[t], reverse=True)[:k]
    idcg = 0.0
    for i, topic in enumerate(ideal_topics):
        rel = max(true_relevance.get(topic, 0.0), 0.0)
        idcg += (2.0 ** rel - 1.0) / math.log2(i + 2)

    if idcg <= 1e-9:
        return 1.0 if dcg <= 1e-9 else 0.0

    return round(dcg / idcg, 4)
import json
from pathlib import Path

def read_records(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open('r', encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]
