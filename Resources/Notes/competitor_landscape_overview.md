# Reading Note: 预测类 Agent 竞品全景对比

## Basic Information

- Source: 联网调研（FutureSearch、Preseen、TrendIntel、Nextatlas、AIA Forecaster、ForeDreamer、Metaculus、Gartner 等）
- Author or Organization: 综合调研
- Publication Date: 各竞品最新公开信息（截至 2026-09）
- Access Date: 2026-09-02
- URL: 见 `Project_Introductions/` 下各分类文件
- Local File: `Resources/Notes/competitor_landscape_overview.md`

## 中文摘要

本次调研覆盖了社会上已公开的预测类 Agent 竞品，分为四大类：商业预测平台（事件/市场预测）、技术趋势预测平台、学术研究系统、开源预测工具，以及传统预测方法论与基准。

核心发现：预测类 Agent 领域已相当成熟，但**技术趋势预测**（本项目定位）与**事件预测**（多数竞品定位）存在显著差异。最接近本项目的竞品是 TrendIntel、TrendOS 和 Nextatlas，它们同样监控学术、专利、开发者社区等上游信号来预测技术趋势。学术研究中，AIA Forecaster 的三层架构和 ForeDreamer 的双记忆架构对本项目最有参考价值。

## Main Contributions

1. **梳理了预测类 Agent 的完整竞品全景**：从商业产品到开源工具到学术研究到传统方法论
2. **识别了本项目的差异化定位**：跨领域技术趋势预测 + 自设计 Agent 架构 + 可复现低计算量方法
3. **提炼了可借鉴的关键技术方案**：趋势分期模型、多 Agent 分工、记忆架构、偏差校准、结构化优先

## Method and Evidence

- Problem: 本项目需要了解社会上已有哪些预测类 Agent，以确定差异化定位和可借鉴的技术方案
- Method: 联网检索各竞品官网、GitHub 仓库、学术论文，整理分类对比
- Data: 20+ 竞品产品的公开信息
- Evaluation: 按"与本项目相关度"分级评估
- Limitations:
  - 部分商业产品方法论不公开（Trendtracker、Nextatlas）
  - 调研基于公开信息，可能遗漏未公开的内部系统
  - 各竞品的实际效果难以横向比较（评测基准不统一）

## 竞品分类对比

### 维度一：预测目标

| 预测目标 | 代表竞品 | 与本项目关系 |
|----------|----------|-------------|
| 事件预测（"会不会发生"） | FutureSearch、Preseen、PolyBridge、Metaculus | 方法论参考 |
| 市场预测（价格/回报） | Predict.ai、Scanna、Crypmatic | 较远 |
| 技术趋势预测（"什么会火"） | TrendIntel、Nextatlas、TrendOS、AimFast | **直接竞品** |
| 时序预测（数值序列） | TimeSeriesScientist、sktime-agentic | 部分参考 |

本项目属于**技术趋势预测**，最直接的竞品是 TrendIntel、TrendOS 和 AimFast.Dev。

### 维度二：数据源

| 数据源类型 | 使用该源的竞品 | 本项目是否覆盖 |
|------------|----------------|----------------|
| 学术论文 | TrendIntel、TrendOS、AimFast、学术研究 | ✅ OpenAlex + Crossref |
| 专利 | TrendIntel、TrendOS | ❌ 未覆盖 |
| 开发者社区 | TrendIntel、TrendOS、AimFast | ✅ GitHub（部分） |
| 新闻/事件 | AIA Forecaster、GDELT 相关 | ✅ GDELT |
| 社交媒体 | AimFast、AIsa | ❌ 未覆盖 |
| 预测市场 | FutureSearch、PolyBridge、AIsa | ❌ 未覆盖 |
| 招聘市场 | TrendIntel、TrendOS | ❌ 未覆盖 |
| 早期采纳者 | Nextatlas | ❌ 未覆盖 |

**差距**：本项目当前 4 个数据源（OpenAlex、Crossref、GDELT、GitHub）覆盖了最核心的学术+新闻+代码信号，但缺少专利、社交媒体、招聘市场等信号源。

### 维度三：架构设计

| 架构模式 | 代表竞品 | 特点 |
|----------|----------|------|
| 多 Agent 分工 | FutureSearch、TSci、本项目 | 不同 Agent 负责不同阶段 |
| 主+子 Agent | ForeDreamer、AIA | 主 Agent 推理，子 Agent 处理证据 |
| 多认知 Agent | MCA | 多视角消除偏差 |
| 群体模拟 | Crypmatic | 万级 Agent 模拟共识 |
| 单 Agent + RAG | Simplicity paper | 简单 RAG 可能优于复杂 Agent |

本项目采用**多 Agent 分工**（DataCollection→DataAnalysis→Prediction→Report），与 TSci 的四 Agent 架构高度对应。

### 维度四：记忆设计

| 记忆模式 | 代表竞品 | 特点 |
|----------|----------|------|
| 共享世界模型 | FutureSearch | 跨预测任务共享世界状态 |
| 双记忆（事实+经验） | ForeDreamer | 事实记忆单问题，经验记忆跨问题 |
| 自进化记忆 | ForeDreamer | 文本+程序经验自动更新 |
| 无持久记忆 | 多数竞品 | 每次预测独立 |

本项目有 `Memory_Design/` 实验分类，ForeDreamer 是最直接的参考。

### 维度五：趋势评分方法

| 评分方法 | 代表竞品 | 特点 |
|----------|----------|------|
| 阶段分期 | Gartner(5阶段)、TrendIntel(Stage 0-5)、TrendOS(Genesis→Saturation) | 离散阶段 |
| 加权评分 | AimFast(四维加权)、TrendOS(0-100) | 连续分数 |
| 动量加速度 | TrendIntel(8周滚动) | 信号变化速度 |
| 双轴定位 | Tech Opportunity Discovery(增长潜力×文献特征) | 二维定位 |
| 跨平台验证 | AimFast(≥2平台) | 信号可信度 |

本项目应设计自己的趋势评分体系，可综合借鉴：阶段分期 + 加权评分 + 动量加速度 + 跨源验证。

## Relevance to Predictive Agents

- Useful idea:
  1. **ForeDreamer 双记忆架构**：事实记忆（单问题证据）+ 经验记忆（跨问题经验）→ 本项目 `Memory_Design/` 的核心参考
  2. **AIA Forecaster 三层架构**：Agentic search + Supervisor + 校准 → 本项目多数据源调和的参考
  3. **AimFast 四维评分**：渠道多样性 + 信号强度 + 参与速度 + 跨平台传播 → 本项目趋势评分的设计参考
  4. **Simplicity paper 警示**：结构化统计 > 非结构化文本，简单 RAG 可能 > 复杂 Agent → 不要过度设计
  5. **Tech Opportunity Discovery 双轴定位**：预测增长潜力 × 当前文献特征 → 本项目趋势定位的可视化参考

- Possible implementation:
  1. 趋势评分 = 加权(论文加速度, 引用集中度, 事件频率, GitHub 活跃度) + 跨源验证
  2. 趋势分期 = 类似 Gartner 五阶段但用定量指标判定
  3. 记忆架构 = ForeDreamer 式双记忆（事实+经验）
  4. 偏差校准 = AIA 式统计校准

- Assumptions to verify:
  1. OpenAlex + Crossref + GDELT + GitHub 四源是否足够？是否需要加专利（USPTO/Google Patents）？
  2. 结构化指标是否确实优于纯 LLM 推理？（Simplicity paper 支持但需在本项目场景验证）
  3. 多 Agent 分工是否真的优于简单 RAG pipeline？（取决于任务复杂度）
  4. LLM 预测在技术趋势（长期、模糊）上是否比事件预测（短期、明确）更难？

- Related attempts:
  - 本项目 `Memory_Design/`：可参考 ForeDreamer
  - 本项目 `Reasoning_Architecture/`：可参考 AIA、TSci、MCA
  - 本项目 `Baselines/`：可用 FutureSearch SDK 作为外部基线

## Follow-up

- [ ] 深入阅读 ForeDreamer 论文和代码，提取记忆架构设计细节
- [ ] 深入阅读 AIA Forecaster 技术报告，提取校准方法
- [ ] 试用 FutureSearch API，对本项目跟踪的 6 个主题做对比预测
- [ ] 评估是否需要增加专利数据源（USPTO PatentsView / Google Patents API）
- [ ] 设计本项目的趋势评分体系（综合 AimFast 四维 + TrendIntel 动量 + Gartner 分期）
- [ ] 在 `Attempt/Baselines/` 中实现简单 RAG 基线，与多 Agent 架构对比（验证 Simplicity paper 的发现）
