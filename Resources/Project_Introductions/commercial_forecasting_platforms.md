# 商业预测平台 — 事件/市场预测类

> 调研日期：2026-09-02
> 调研方式：联网检索各产品官网和公开资料

这些平台主要面向"某个事件会不会发生"的预测，通常以预测市场（Polymarket、Kalshi）或 forecasting tournament（Metaculus）为评测场景。

---

## 1. FutureSearch

- **官网**：https://futuresearch.ai
- **公司**：Varuna AI, Inc.，2023 年成立，总部 San Bruno, CA
- **创始人**：Dan Schwarz（前 Metaculus CTO）、Lawrence Phillips
- **融资**：Seed $6.2M（2024-11）
- **核心定位**：AI 预测平台，"Search the Future"

### 产品能力

- 支持多种预测类型：概率（二值）、数值、日期、分类、条件预测、决策预测
- 多 Agent 架构：部署 AI 研究 Agent 团队进行结构化数据研究
- **共享世界模型（World Modeling）**：跨数千次预测共享同一个世界状态模型，是首个被验证能提升准确度的此类设计
- 提供 MCP connector，可接入 Claude.ai / Claude Code
- 提供 Python SDK（`futuresearch-python`，MIT 协议）
- 定价：$0.15–$2/问题

### 公开成绩

- Metaculus FutureEval 排名 #1（2026 夏季赛，166 个 AI 系统中）
- ForecastBench 排名 #17/377
- Kalshi 实盘组合年化回报 91%（扣费后）
- 超过 3,500 用户

### 技术亮点（与本项目相关）

- **共享世界模型**：跨预测任务维护统一的世界状态——本项目可借鉴的"长期记忆"设计
- **多 Agent 研究团队**：不同 Agent 负责不同信息源的研究
- **Bench to the Future (BTF) 基准**：自建离线预测基准，1,417 个难题，15M 文档语料库，避免数据泄漏

### 局限

- 主要面向事件预测，不直接做技术趋势/新兴技术预测
- 依赖商业 LLM API，成本较高
- 闭源核心系统

---

## 2. Preseen

- **官网**：https://preseen.com
- **核心定位**："最富战绩的预测 bot"

### 产品能力

- 面向金融、政治、全球事件的 AI 预测
- 公开预测记录：Preseen-Atlas、Preseen-Chestnut
- 在预测市场实盘操作：$35 起步做到 $1.94M（50,000× 回报）

### 公开成绩

- FutureEval Bot Tournament（Metaculus bot-only 赛）：史上最佳 bot 表现
- Metaculus Market Pulse：首个在人类锦标赛中获胜的 bot
- 实盘覆盖 Kalshi、Polymarket、S&P 500

### 与本项目关系

- 实盘验证了 AI 预测的可行性
- 但聚焦短期事件预测，非技术趋势

---

## 3. PolyBridge

- **官网**：https://polybridge.ai
- **核心定位**：基于真实市场信号的预测，因果推理驱动

### 产品能力

- 融合 170,000+ 预测市场数据 + 新闻 + 私有数据源
- 显式因果推理模型，支持条件预测和反事实推理
- 输出带置信区间的概率，而非单点估计
- 完整审计链：每个概率可追溯到贡献的市场和信号源
- 提供 Search / Forecast / RVOL API 端点
- 支持 MCP，可被 AI agent 调用

### 技术亮点

- **因果推理 + 市场信号融合**：不依赖单一市场，能回答"没有任何单一市场覆盖的问题"
- **可追溯性**：每个预测都有完整的证据链——本项目的"可解释预测"可参考

---

## 4. Predict.ai

- **官网**：https://predict.ai
- **核心定位**："The Prediction OS"——通用预测操作系统

### 产品能力

- 自动发现驱动因子（driver discovery）：按滞后和评分排序信号
- 自动特征工程：滞后、滚动统计、事件特征
- 模型锦标赛：在相同数据上回测多个模型，部署最强者
- Agent 可通过 MCP 创建和查询预测
- 支持反事实分析（what-if）：改变驱动因子或调度事件，对比基线预测

### 技术亮点

- **驱动因子发现 + 自动建模**：从原始数据到预测全自动化
- **MCP 原生**：Agent 可直接调用预测能力
- 适合时间序列预测场景

---

## 5. AIsa Trend Forecast

- **官网**：https://aisa.one/skills/trend-forecast
- **核心定位**：AI Agent Skill，多信号融合趋势预测

### 产品能力

- 分解用户预测问题
- 融合多信号源：
  - Polymarket / Kalshi 预测市场赔率
  - X/Twitter 社交情绪
  - Tavily 新闻速度
  - 股票/宏观信号
- 用 AIsa 模型综合生成带置信评分的趋势报告
- 作为 Agent Skill 提供，可被其他 AI agent 调用

### 与本项目关系

- **多信号融合**思路与本项目的多数据源（OpenAlex + GDELT + GitHub + Crossref）类似
- 但 AIsa 聚焦短期事件，本项目聚焦长期技术趋势

---

## 6. Scanna

- **官网**：https://scanna.xyz
- **核心定位**：预测市场的 Agent 原生情报层

### 产品能力

- 标准化预测市场数据 + 分析信号 + 模型输出 + 钱包分析 + 跨市场对比
- Heat scores、巨鲸活动、多因子信号分析、A–F 风险评级
- 跨场所套利检测：Polymarket vs Kalshi 价格分歧
- 提供 REST API + MCP server + TypeScript/Python 客户端
- x402 支付协议支持

### 与本项目关系

- 主要服务预测市场交易 Agent，与技术趋势预测关联较弱
- 但"标准化多市场数据 + 结构化信号"的思路可参考

---

## 7. Crypmatic

- **官网**：https://crypmatic.com
- **核心定位**：万级 Agent 模拟共识预测

### 产品能力

- 部署 1,000–10,000 个带真实人设的 AI Agent
- 模拟市场、消费者和组织行为
- 用结构化、可审计的模拟替代猜测
- 适用于任何行业

### 技术亮点

- **大规模 Agent 模拟**：用海量带人设的 Agent 模拟群体行为得出共识预测
- 与本项目的"多 Agent"思路不同——Crypmatic 是"群体模拟"，本项目是"分工协作"

---

## 小结

| 产品 | 预测类型 | 核心方法 | 开放程度 | 与本项目相关度 |
|------|----------|----------|----------|----------------|
| FutureSearch | 事件/市场 | 多 Agent + 共享世界模型 | SDK 开源，核心闭源 | 高（架构参考） |
| Preseen | 事件/市场 | 预测市场实盘 | 闭源 | 中 |
| PolyBridge | 事件/市场 | 因果推理 + 市场融合 | API 开放 | 中（可追溯性） |
| Predict.ai | 时序/通用 | 驱动因子发现 + 模型锦标赛 | API/MCP | 中（自动化） |
| AIsa | 趋势/事件 | 多信号融合 | Agent Skill | 高（多信号源） |
| Scanna | 预测市场 | 市场情报层 | API/MCP | 低 |
| Crypmatic | 群体模拟 | 万级 Agent 模拟 | 闭源 | 低 |
