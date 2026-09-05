# 学术研究系统 — LLM 预测相关论文与系统

> 调研日期：2026-09-02
> 调研方式：联网检索 arXiv、ACL Anthology、GitHub

本文件收录与 LLM 预测/事件预测/技术趋势预测相关的学术论文和研究系统。这些工作提供了可借鉴的架构设计、方法论和评测基准。

---

## 1. AIA Forecaster

- **来源**：arXiv:2511.07678（技术报告）
- **核心定位**：基于 LLM 的判断性预测系统，使用非结构化数据

### 方法

三大核心要素：
1. **Agentic search**：对高质量新闻源进行 Agent 式搜索
2. **Supervisor agent**：调和同一事件的多方预测分歧
3. **统计校准技术**：对抗 LLM 的行为偏差

### 成绩

- ForecastBench 基准上达到**人类超级预测者水平**，超越先前所有 LLM 基线
- 引入更难的预测市场基准（1,610 个来自流动性预测市场的问题）
- 在预测市场基准上略逊于市场共识，但**AIA + 市场共识的集成超越单独共识**——证明系统提供了增量信息
- 据作者所知，这是**首个在大规模上可验证达到专家级预测水平**的工作

### 与本项目关系

- **极高参考价值**：Agentic search + Supervisor + 校准的三层架构可直接借鉴
- "调和多方预测"的 Supervisor agent 设计适用于本项目的多数据源场景
- 统计校准对抗 LLM 偏差是重要工程实践

---

## 2. MCA (Multi-Cognition Agentic Framework) + CogForecast

- **来源**：ACL 2025 Findings（2025.findings-emnlp.258）
- **核心定位**：消除 LLM 事件预测中的认知偏差

### 背景

LLM 在事件预测中表现出类人认知偏差——系统性偏离理性的决策模式。

### 方法

- 引入 CogForecast 数据集：6 个话题的人工策展数据集
- MCA 框架：
  1. 让 LLM 扮演多认知事件参与者，基于事件参与者的认知模式进行视角转换
  2. 按预测聚类 Agent
  3. 通过组级可靠性评分得出最终答案
- 用 Llama-3.1-70B 达到 82.3% 准确率（人类群体 79.5%）

### 与本项目关系

- **认知偏差消除**是本项目需要关注的问题——LLM 可能对某些技术趋势有系统性偏差
- "多认知视角 + 聚类 + 可靠性评分"的集成方法可参考
- CogForecast 数据集可作为评测参考

---

## 3. OpenForecaster

- **来源**：arXiv:2512.25070
- **核心定位**：开源 RL 训练的预测模型

### 方法

- 从每日新闻中合成预测问题，全自动策展
- 用 Qwen3 thinking 模型在 OpenForesight 数据集上训练
- 使用离线新闻语料库（避免未来信息泄漏）
- 检索增强 + 改进的 RL 奖励函数
- OpenForecaster8B 匹配大得多的专有模型
- 训练提升预测的准确性、校准和一致性
- 校准改进泛化到其他流行基准

### 与本项目关系

- **完全开源**（模型、代码、数据）——可作为基线或起点
- RL 训练预测模型的思路值得关注
- "离线语料库避免数据泄漏"是重要方法论

---

## 4. ForeDreamer

- **来源**：EMNLP 2026 Findings，arXiv:2608.20920
- **代码**：https://github.com/zhongzero/ForeDreamer
- **核心定位**：自进化的双 Agent 记忆架构，用于未来事件预测

### 核心理念

将开放网络预测视为**"证据到记忆的转换"问题**：原始搜索结果在预测 Agent 推理之前，先被转换为结构化的、问题特定的事实记忆。

### 架构

两种记忆形式：
- **事实记忆（Factual memory）**：单个预测问题的已处理证据状态
- **经验记忆（Experiential memory）**：跨预测事件持久化，指导未来的搜索、证据处理和预测

框架组件：
- **主 Agent**：规划截止时间感知的网页搜索，产出预测
- **记忆处理子 Agent**：遵循 MemGuide，执行沙盒化 MemTools，将搜索结果转换为事实记忆
- **文本经验进化**：更新 Experience Bank（搜索规划、证据整合、校准）
- **程序经验进化**：更新 MemGuides 和可执行 MemTools
- **组合工具复用 + 多样性引导探索**：减少冗余、增加程序进化的多样性

### 与本项目关系

- **极高参考价值**：本项目有 `Memory_Design/` 实验分类，ForeDreamer 的双记忆架构直接相关
- "证据到记忆转换"的思路适用于本项目的数据预处理
- "经验记忆跨任务持久化"对应本项目的长期记忆设计
- "自进化"（文本 + 程序）是高级记忆管理思路

---

## 5. Prophet Arena

- **来源**：arXiv:2510.17638
- **核心定位**：LLM 预测能力评测基准——"LLM-as-a-Prophet"

### 方法

- 持续收集实时预测任务
- 每个任务分解为不同的 pipeline 阶段
- 多评分指标：统计准确性、校准、经济价值
- 在 1,300+ 已解决的真实事件上评估

### 发现

- 许多 LLM 已展现令人印象深刻的预测能力（小校准误差、一致的预测置信度、有前景的市场回报）
- 关键瓶颈：不准确的事件回忆、对数据源的误解、接近事件解决时信息聚合速度慢于市场

### 与本项目关系

- 可作为**评测框架参考**
- "pipeline 阶段分解"的评估思路值得借鉴
- 指出的 LLM 预测瓶颈是本项目需要解决的问题

---

## 6. TimeSeriesScientist (TSci)

- **来源**：GitHub: BenCheng2/TimeSeriesScientist
- **核心定位**：首个 LLM 驱动的通用时序预测 Agent 框架

### 架构（四个专门化 Agent）

1. **Curator**：LLM 引导的诊断 + 外部工具，基于数据统计选择针对性预处理
2. **Planner**：利用多模态诊断和自规划缩小模型选择假设空间
3. **Forecaster**：模型拟合和验证，自适应选择最佳模型配置和集成策略
4. **Reporter**：综合全过程生成透明报告

### 技术特点

- 基于 LangGraph 的多 Agent 工作流
- 白盒系统：可解释、可扩展
- LLM 决定集成策略

### 与本项目关系

- 四 Agent 分工（Curator→Planner→Forecaster→Reporter）与本项目的多 Agent 架构（DataCollection→DataAnalysis→Prediction→Report）高度对应
- "白盒可解释"是本项目追求的目标

---

## 7. "The Power of Simplicity in LLM-Based Event Forecasting"

- **来源**：REALM 2025 Workshop（2025.realm-1.32）
- **核心发现**：简化 ReAct 为 RAG pipeline，仅用 10% token 成本就超越 ReAct

### 关键发现

- 结构化统计上下文显著提升预测准确性
- 非结构化语义信息（如新闻标题）反而**损害**性能
- 迭代推理 trace 在小模型中损害准确性，但在大模型（如 70B）中有益

### 与本项目关系

- **重要警示**：不是越复杂的 Agent 架构越好，简单 RAG 可能更有效
- "结构化统计 > 非结构化文本"的发现支持本项目用结构化指标（论文计数、引用量、事件频率）而非纯文本推理
- 模型规模与推理方式的交互效应需要考虑

---

## 8. 文献计量 + LLM 技术机会发现

### 8a. "Discovering Technology Opportunities Based on LLM and Bibliometric Indicators"

- **来源**：IEEE CASCON 2025（10.1109/cascon66301.2025.00099）
- **方法**：
  - LLM 预测技术未来增长潜力
  - 提取定量文献计量特征表示当前状态
  - 构建技术机会图：预测增长潜力 × 当前文献特征
  - 四类分型：稳定增长、成熟技术、停滞技术、新兴技术机会

### 8b. "Monitoring Transformative Technological Convergence Through LLM-Extracted Semantic Entity Triple Graphs"

- **来源**：arXiv:2510.25370
- **方法**：
  - LLM 从非结构化文本提取语义三元组
  - 构建大规模技术实体-关系图
  - 图指标 + 聚类检测技术融合信号
  - 在 278,625 篇 arXiv 预印本（2017–2024）上验证
  - 追踪下游商业化应用

### 与本项目关系

- **8a** 的"LLM 预测 + 文献计量"双轴定位图可直接借鉴——本项目可做"预测增长潜力 × 当前文献特征"的趋势定位
- **8b** 的"语义三元组图 + 融合信号检测"是更高级的技术方案，适合后续探索
- 两者都用 arXiv 数据，与本项目用 OpenAlex/Crossref 的数据源策略一致

---

## 小结

| 系统/论文 | 核心方法 | 与本项目关系 |
|-----------|----------|-------------|
| AIA Forecaster | Agentic search + Supervisor + 校准 | 极高（架构参考） |
| MCA / CogForecast | 多认知 Agent + 偏差消除 | 高（偏差处理） |
| OpenForecaster | RL 训练 + 离线语料 | 高（开源基线） |
| ForeDreamer | 双 Agent 记忆 + 自进化 | 极高（记忆设计） |
| Prophet Arena | 预测能力评测基准 | 中（评测参考） |
| TimeSeriesScientist | 四 Agent 时序预测 | 高（架构对应） |
| Simplicity paper | RAG > ReAct，结构化 > 非结构化 | 高（方法论警示） |
| Tech Opportunity Discovery | LLM + 文献计量双轴 | 极高（趋势定位） |
| Semantic Triple Graphs | LLM 三元组 + 图融合检测 | 中（后续探索） |

### 对本项目架构的启示

1. **多 Agent 分工**：AIA（search+supervisor+校准）、TSci（curator+planner+forecaster+reporter）、ForeDreamer（主+子）都采用多 Agent 架构——验证了本项目的设计方向
2. **记忆设计**：ForeDreamer 的双记忆（事实+经验）是本项目 `Memory_Design/` 的直接参考
3. **偏差处理**：MCA 和 AIA 都强调校准和偏差消除——本项目需纳入
4. **结构化优先**：Simplicity paper 证明结构化统计优于非结构化文本——支持本项目用定量指标
5. **文献计量 + LLM**：Tech Opportunity Discovery 证明两者结合有效——正是本项目的方向
