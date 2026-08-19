# Experiment: Simple Baseline Forecast

## 中文摘要

这是项目的第一个可运行实验，目标是打通"数据采集 → 数据标准化 → 基线预测 → 评估输出"的完整链路。使用移动平均和线性回归两种简单方法作为基线，为后续 Agent 预测提供对照。

## Objective

- Category: Baselines
- Start Date: 2026-08-14
- Status: running
- Input Data Version: technology_cultivation_00

## Hypothesis

简单统计方法（移动平均、线性回归）可以在技术趋势活动信号上产生合理的预测。如果基线 MAPE < 50%，说明信号有趋势性，值得用更复杂的 Agent 方法改进。

## Design

- Agent or model: 无 Agent，纯统计基线
- Memory design: 无
- Reasoning flow: 无
- Tools or APIs: OpenAlex Works API, GDELT DOC 2.0 API
- Evaluation protocol: 时间序列切分（70% train / 30% test），逐月滚动预测，计算 MAE / MAPE / RMSE

## Setup

```powershell
cd 'F:\Predictive agents\Attempt'
.\.venv\Scripts\Activate.ps1
```

## Run

```powershell
python -m Baselines.experiments.2026-08-14_simple_baseline.src.pipeline
```

## Results

运行后结果保存在 `Data/Reports/technology_cultivation_00/` 下：
- `baseline_results.json` — 每个预测的详细结果
- `baseline_evaluations.json` — 每个预测的评估指标
- `summary.json` — 汇总指标

## Reproducibility Checklist

- [x] Data version: technology_cultivation_00
- [x] Configuration: Attempt/configs/default.yaml + Attempt/configs/topics.yaml
- [x] Exact command recorded
- [x] Dependency versions pinned in requirements.txt
- [x] Random seed: 42 (in default.yaml)
- [x] Outputs and limitations explained

## Next Steps

- 如果基线 MAPE 可接受，进入 Phase 4：设计 Agent 推理架构
- 如果基线 MAPE 过高，检查数据质量和信号强度
- 考虑增加 ARIMA 或 Prophet 作为更强的基线
