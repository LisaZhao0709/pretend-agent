# 开源预测工具

> 调研日期：2026-09-02
> 调研方式：联网检索 GitHub

本文件收录 GitHub 上可获取的开源预测 Agent 工具。这些项目可作为本项目的参考实现、基线或起点。

---

## 1. mini-prophet

- **仓库**：https://github.com/ai-prophet/mini-prophet
- **核心定位**：最小 LLM 预测 Agent 脚手架（受 mini-swe-agent 启发）

### 特点

- 支持多种搜索后端：Perplexity（默认）、Brave、Exa、Tavily
- `dev` 分支包含**规划阶段**：Agent 先产出结构化 XML 计划（分解问题为子查询、子问题和考虑因素），人工审核后再执行研究
- 完整文档：架构、CLI、批量预测 API、Eval CLI、数据集管理、扩展框架、输出格式

### 与本项目关系

- **轻量级参考实现**：适合作为本项目预测 Agent 的最小可行原型
- "规划→审核→执行"的流程值得借鉴
- 多搜索后端抽象的设计可参考

---

## 2. forecast-agents (Forecast AI)

- **仓库**：https://github.com/codebyollie/forecast-agents
- **核心定位**：预测市场的开源多 Agent 智能基础设施

### 特点

- 支持 Kalshi、Robinhood Predict 等预测市场
- 多 Agent 架构
- 开源

### 与本项目关系

- 主要面向预测市场交易，非技术趋势预测
- 多 Agent 基础设施的设计可参考

---

## 3. sktime-agentic-forecaster

- **仓库**：https://github.com/mohammedfirdouss/sktime-agentic-forecaster
- **核心定位**：LLM 驱动的自动时序预测——自然语言→sktime pipeline→预测

### 工作流程

1. 解析 prompt：提取任务、偏好和约束
2. 构建上下文：检查数据集（长度、频率、缺失值）
3. LLM 选择：从 sktime 预测器和转换器的策展注册表中选择
4. 构建 pipeline：JSON spec → 真实的 `TransformedTargetForecaster`
5. 拟合和预测
6. 结构化输出：预测 + pipeline 对象 + LLM 推理

### 支持的 LLM 后端

- Anthropic（Claude，推荐）
- OpenAI（GPT-4o / GPT-4）
- Google Gemini
- LangChain（任意 LLM）

### 可用估计器

- 预测器：NaiveForecaster、ExponentialSmoothing、AutoARIMA 等
- 转换器：Differencer、Detrender 等

### 与本项目关系

- **"LLM 选模型 + 自动建 pipeline"**的思路可用于本项目的预测模型选择
- sktime 是成熟的时序库，本项目可考虑引入
- 但本项目主要不是做数值时序预测，而是技术趋势预测——适用性有限

---

## 4. futuresearch-python

- **仓库**：https://github.com/futuresearch/futuresearch-python
- **协议**：MIT
- **核心定位**：FutureSearch 的 Python SDK

### 特点

- 提供 `forecast()` API：输入 DataFrame（问题），输出预测 + 推理
- 支持二值、数值、日期、分类、阈值化预测模式
- 可做条件预测
- 底层是 FutureSearch 的商业 API

### 与本项目关系

- 可作为**对比基线**：用 FutureSearch API 预测同样的问题，对比本项目结果
- 不是自建系统的参考，而是外部预测能力的调用接口

---

## 5. ForeDreamer（代码开源）

- **仓库**：https://github.com/zhongzero/ForeDreamer
- **论文**：EMNLP 2026 Findings
- **核心定位**：自进化双 Agent 记忆架构（详见 `academic_forecasting_systems.md`）

### 与本项目关系

- **记忆设计直接参考**：本项目 `Memory_Design/` 实验可直接借鉴
- 代码可用，适合深入分析其记忆架构实现

---

## 小结

| 项目 | 类型 | 开放程度 | 与本项目关系 |
|------|------|----------|-------------|
| mini-prophet | 预测 Agent 脚手架 | 完全开源 | 高（最小原型参考） |
| forecast-agents | 预测市场多 Agent | 完全开源 | 中（架构参考） |
| sktime-agentic-forecaster | 时序自动建模 | 完全开源 | 中（模型选择思路） |
| futuresearch-python | 商业 API SDK | MIT | 中（对比基线） |
| ForeDreamer | 记忆架构研究 | 完全开源 | 极高（记忆设计） |

### 使用建议

1. **mini-prophet**：作为本项目预测 Agent 的最小可行原型起点
2. **ForeDreamer**：作为 `Memory_Design/` 实验的核心参考
3. **futuresearch-python**：作为评测对比的外部基线
4. **sktime-agentic-forecaster**：如果本项目需要数值时序预测组件，可考虑集成
