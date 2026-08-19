"""AI-powered report generator with data quality gating.

Only calls DeepSeek API when data quality meets a threshold, to avoid
wasting tokens on incomplete results. When data is insufficient, writes
a brief placeholder MD instead.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TIMEOUT = 120

MIN_TOPICS_WITH_DATA = 3
MIN_SIGNALS_WITH_DATA = 2


def _load_env(attempt_root: Path) -> None:
    env_path = attempt_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _get_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        raise ValueError(
            "DEEPSEEK_API_KEY not set. "
            "Please create Attempt/.env with DEEPSEEK_API_KEY=your_key"
        )
    return key


def _check_data_quality(
    pivot: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check how many topics and signals have non-zero data.

    Returns:
        Dict with:
        - topics_with_data: list of topic_ids that have any non-zero count
        - topics_without_data: list of topic_ids with all-zero counts
        - has_openalex: bool, any topic has non-zero openalex_count
        - has_gdelt: bool, any topic has non-zero gdelt_count
        - valid_signals: count of non-zero signals (0, 1, or 2)
        - passed: bool, whether quality meets threshold
    """
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for row in pivot:
        tid = row["topic_id"]
        if tid not in by_topic:
            by_topic[tid] = []
        by_topic[tid].append(row)

    topics_with_data: list[str] = []
    topics_without_data: list[str] = []
    has_openalex = False
    has_gdelt = False

    for tid, rows in by_topic.items():
        oa_vals = [r["openalex_count"] for r in rows]
        gd_vals = [r["gdelt_count"] for r in rows]
        oa_has = any(v > 0 for v in oa_vals)
        gd_has = any(v > 0 for v in gd_vals)
        if oa_has or gd_has:
            topics_with_data.append(tid)
        else:
            topics_without_data.append(tid)
        if oa_has:
            has_openalex = True
        if gd_has:
            has_gdelt = True

    valid_signals = sum([has_openalex, has_gdelt])
    passed = (
        len(topics_with_data) >= MIN_TOPICS_WITH_DATA
        and valid_signals >= MIN_SIGNALS_WITH_DATA
    )

    return {
        "topics_with_data": topics_with_data,
        "topics_without_data": topics_without_data,
        "has_openalex": has_openalex,
        "has_gdelt": has_gdelt,
        "valid_signals": valid_signals,
        "passed": passed,
    }


def _write_insufficient_report(
    report_path: Path,
    quality: dict[str, Any],
) -> None:
    """Write a placeholder MD when data quality is insufficient."""
    lines = [
        "# 技术趋势预测分析报告（数据不完整）",
        "",
        f"> 报告生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 数据质量检查未通过",
        "",
        "本次实验数据不完整，已跳过 AI 分析以节约 API 用量。",
        "",
        "### 检查结果",
        "",
        f"- 有数据的主题数: {len(quality['topics_with_data'])} (要求 >= {MIN_TOPICS_WITH_DATA})",
        f"- 有效信号源数: {quality['valid_signals']} (要求 >= {MIN_SIGNALS_WITH_DATA})",
        f"- OpenAlex 论文数据: {'有' if quality['has_openalex'] else '无'}",
        f"- GDELT 新闻数据: {'有' if quality['has_gdelt'] else '无'}",
        "",
        "### 有数据的主题",
        "",
    ]
    for tid in quality["topics_with_data"]:
        lines.append(f"- {tid}")
    if not quality["topics_with_data"]:
        lines.append("- （无）")

    lines.extend([
        "",
        "### 无数据的主题",
        "",
    ])
    for tid in quality["topics_without_data"]:
        lines.append(f"- {tid}")
    if not quality["topics_without_data"]:
        lines.append("- （无）")

    lines.extend([
        "",
        "## 下一步",
        "",
        "1. 等待 API 限流重置后重新运行 pipeline",
        "2. 确认 OpenAlex 和 GDELT 两个数据源都有非零数据",
        "3. 确认至少 3 个主题有有效数据",
        "4. 数据质量达标后，AI 分析报告将自动生成",
        "",
    ])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _build_data_summary(
    evaluations: list[dict[str, Any]],
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    pivot: list[dict[str, Any]],
) -> str:
    lines: list[str] = []

    lines.append("## 实验概况")
    lines.append(f"- 评估总数: {summary['total']}")
    lines.append(f"- 平均 MAE: {summary['avg_mae']:.2f}")
    lines.append(f"- 平均 MAPE: {summary['avg_mape']:.1f}%")
    lines.append(f"- 平均 RMSE: {summary['avg_rmse']:.2f}")
    lines.append("")

    lines.append("## 各方法汇总")
    for method, ms in summary.get("by_method", {}).items():
        lines.append(
            f"- {method}: avg_mae={ms['avg_mae']:.2f}, "
            f"avg_mape={ms['avg_mape']:.1f}%, "
            f"avg_rmse={ms['avg_rmse']:.2f}, count={ms['count']}"
        )
    lines.append("")

    lines.append("## 各 Topic 各方法详细评估")
    for ev in evaluations:
        lines.append(
            f"- topic={ev['topic_label']}, signal={ev['column']}, "
            f"method={ev['method']}, MAE={ev['mae']:.2f}, "
            f"MAPE={ev['mape']:.1f}%, RMSE={ev['rmse']:.2f}, "
            f"test_size={ev['test_size']}"
        )
    lines.append("")

    lines.append("## 各 Topic 时间序列数据概览")
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for row in pivot:
        tid = row["topic_id"]
        if tid not in by_topic:
            by_topic[tid] = []
        by_topic[tid].append(row)

    for tid, rows in sorted(by_topic.items()):
        rows_sorted = sorted(rows, key=lambda r: r["window_start"])
        label = rows_sorted[0]["topic_label"]
        oa_values = [r["openalex_count"] for r in rows_sorted]
        gd_values = [r["gdelt_count"] for r in rows_sorted]
        time_range = f"{rows_sorted[0]['window_start']} ~ {rows_sorted[-1]['window_start']}"

        lines.append(f"### {label} ({tid})")
        lines.append(f"- 时间范围: {time_range} ({len(rows_sorted)} 个月)")
        if any(v > 0 for v in oa_values):
            lines.append(
                f"- OpenAlex 论文计数: min={min(oa_values)}, "
                f"max={max(oa_values)}, "
                f"mean={sum(oa_values)/len(oa_values):.1f}, "
                f"首5月={oa_values[:5]}, 末5月={oa_values[-5:]}"
            )
        else:
            lines.append("- OpenAlex 论文计数: 全部为 0（数据未采集或限流）")
        if any(v > 0 for v in gd_values):
            lines.append(
                f"- GDELT 新闻计数: min={min(gd_values)}, "
                f"max={max(gd_values)}, "
                f"mean={sum(gd_values)/len(gd_values):.1f}, "
                f"首5月={gd_values[:5]}, 末5月={gd_values[-5:]}"
            )
        else:
            lines.append("- GDELT 新闻计数: 全部为 0（数据未采集或限流）")
        lines.append("")

    lines.append("## 预测 vs 实际对比（有数据的 topic）")
    for res in results:
        actuals = res["actuals"]
        preds = res["predictions"]
        if all(v == 0 for v in actuals):
            continue
        lines.append(
            f"### {res['topic_label']} — {res['column']} — {res['method']}"
        )
        lines.append(f"- 测试窗口: {res['test_windows']}")
        lines.append(f"- 实际值: {[int(v) for v in actuals]}")
        lines.append(f"- 预测值: {[round(v, 1) for v in preds]}")
        diffs = [abs(a - p) for a, p in zip(actuals, preds)]
        lines.append(f"- 绝对误差: {[round(d, 1) for d in diffs]}")
        lines.append("")

    return "\n".join(lines)


def _build_prompt(data_summary: str) -> str:
    return f"""你是一位技术趋势分析专家。请根据以下实验数据，撰写一份中文 Markdown 分析报告。

要求：
1. 用通俗易懂的语言解释每个指标（MAE、MAPE、RMSE）的含义
2. 分析每个技术主题的趋势变化（上升/下降/波动）
3. 比较两种基线方法（移动平均 vs 线性回归）的表现差异
4. 指出哪些主题的预测效果好、哪些不好，并分析可能的原因
5. 对数据质量给出评价（是否有缺失、限流影响）
6. 给出下一步改进建议
7. 报告以 `# 技术趋势预测分析报告` 为标题
8. 使用 Markdown 格式，包含表格和列表

以下是实验数据：

{data_summary}
"""


def call_deepseek(prompt: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "你是一位专业的技术趋势分析师，擅长用中文撰写清晰易懂的分析报告。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    resp = requests.post(
        DEEPSEEK_BASE_URL,
        headers=headers,
        json=payload,
        timeout=DEEPSEEK_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def generate_report(
    reports_path: Path,
    attempt_root: Path,
    force: bool = False,
) -> Path:
    """Generate AI-powered Markdown analysis report from saved results.

    Only calls DeepSeek API when data quality meets threshold.
    Otherwise writes a placeholder MD without consuming API tokens.

    Args:
        reports_path: Directory containing result JSON files.
        attempt_root: Attempt/ root directory (for .env loading).
        force: If True, skip quality check and always call API.

    Returns:
        Path to the generated .md report file.
    """
    _load_env(attempt_root)

    with open(reports_path / "baseline_results.json", "r", encoding="utf-8") as f:
        results = json.load(f)
    with open(reports_path / "baseline_evaluations.json", "r", encoding="utf-8") as f:
        evaluations = json.load(f)
    with open(reports_path / "summary.json", "r", encoding="utf-8") as f:
        summary = json.load(f)

    pivot_path = reports_path.parent.parent / "Processed" / "technology_cultivation_00" / "pivot_table.jsonl"
    pivot: list[dict[str, Any]] = []
    if pivot_path.exists():
        with open(pivot_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    pivot.append(json.loads(line))

    report_path = reports_path / "analysis_report.md"

    quality = _check_data_quality(pivot)
    topics_ok = len(quality["topics_with_data"])
    signals_ok = quality["valid_signals"]

    if not force and not quality["passed"]:
        print(f"  Data quality check: {topics_ok} topics with data, {signals_ok} signals with data")
        print(f"  Threshold: >={MIN_TOPICS_WITH_DATA} topics, >={MIN_SIGNALS_WITH_DATA} signals")
        print(f"  SKIPPED API call to save tokens. Writing placeholder report.")
        _write_insufficient_report(report_path, quality)
        print(f"  Placeholder report saved: {report_path}")
        return report_path

    print(f"  Data quality check passed: {topics_ok} topics, {signals_ok} signals")

    data_summary = _build_data_summary(evaluations, results, summary, pivot)
    prompt = _build_prompt(data_summary)

    api_key = _get_api_key()
    print("  Calling DeepSeek API for analysis...")
    start = time.perf_counter()
    report_text = call_deepseek(prompt, api_key)
    duration = (time.perf_counter() - start) * 1000
    print(f"  DeepSeek response received ({duration:.0f}ms, {len(report_text)} chars)")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"  Report saved: {report_path}")
    return report_path
