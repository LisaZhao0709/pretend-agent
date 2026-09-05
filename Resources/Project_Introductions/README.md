# Project Introductions — 预测类 Agent 竞品调研

本目录收录社会上已公开的预测类 Agent 产品、开源项目、学术研究和传统方法论，作为本项目（Predictive Agents）的对标参考。

## 调研范围

调研于 2026-09-02 进行，覆盖以下四类竞品：

| 分类 | 文件 | 说明 |
|------|------|------|
| 商业预测平台 | `commercial_forecasting_platforms.md` | 面向事件/市场预测的 AI Agent 产品 |
| 技术趋势预测平台 | `tech_trend_platforms.md` | 面向技术趋势/新兴技术预测的平台 |
| 学术研究系统 | `academic_forecasting_systems.md` | LLM 预测相关的学术论文和研究系统 |
| 开源预测工具 | `opensource_forecasting_tools.md` | GitHub 上可获取的开源预测 Agent |
| 传统预测方法论 | `traditional_methodologies.md` | Gartner Hype Cycle、Metaculus、Good Judgment 等 |

## 竞品全景图

```
预测类 Agent 竞品
├── 事件/市场预测（"会不会发生"）
│   ├── FutureSearch        — Metaculus #1，多 Agent + 共享世界模型
│   ├── Preseen             — 预测市场实战，50,000× 回报
│   ├── PolyBridge          — 预测市场信号融合 + 因果推理
│   ├── Predict.ai          — 通用预测 OS，MCP 驱动
│   ├── AIsa Trend Forecast — Agent Skill，融合多信号源
│   ├── Scanna              — 预测市场情报层
│   └── Crypmatic           — 万级 Agent 模拟共识预测
│
├── 技术趋势预测（"什么会火"）
│   ├── TrendIntel          — 上游信号（开发者/学术/专利）
│   ├── Nextatlas           — 早期采纳者行为，提前 30 个月
│   ├── AimFast.Dev         — 28+ 平台信号扫描 + 评分
│   ├── Trendtracker        — 企业级战略情报平台
│   └── TrendOS             — 地下趋势检测，提前 173 天
│
├── 学术研究系统
│   ├── AIA Forecaster      — 达到人类超级预测者水平
│   ├── MCA / CogForecast   — 多认知 Agent 消除认知偏差
│   ├── OpenForecaster      — 开源 RL 训练预测模型
│   ├── ForeDreamer         — 双 Agent 记忆架构
│   ├── Prophet Arena       — LLM 预测能力评测基准
│   └── TimeSeriesScientist — 时序预测多 Agent 框架
│
├── 开源工具
│   ├── mini-prophet        — 最小 LLM 预测 Agent 脚手架
│   ├── forecast-agents     — 预测市场多 Agent 基础设施
│   ├── sktime-agentic-forecaster — sktime + LLM 自动建模
│   └── futuresearch-python — FutureSearch SDK
│
└── 传统方法论与基准
    ├── Gartner Hype Cycle  — 技术成熟度五阶段模型
    ├── Metaculus           — 人类预测平台 + AI 基准测试
    ├── Good Judgment Project — 超级预测者方法论
    └── ForecastBench       — 无污染预测能力基准
```

## 与本项目的关系

本项目（Predictive Agents）定位为**跨领域技术趋势预测 Agent**，与上述竞品的关系：

- **最接近的竞品**：技术趋势预测平台（TrendIntel、Nextatlas、TrendOS）——同样关注"什么技术会兴起"
- **方法论参考**：学术研究系统（AIA Forecaster、MCA、ForeDreamer）——多 Agent 架构、记忆设计、偏差消除
- **评测对标**：Metaculus AI Benchmark、ForecastBench——可作为评测框架参考
- **差异化方向**：本项目聚焦"跨领域"和"自设计 Agent 架构"，多数竞品要么聚焦事件预测（会不会发生），要么聚焦单一领域趋势
