# 预测智能体项目 - 技术框架总结报告

**生成时间**：2026-08-17  
**项目根目录**：`F:\Predictive agents`  
**报告类型**：完整技术框架分析与文档生成

---

## 执行摘要

本报告对**预测智能体（Predictive Agents）**项目进行了全面的技术框架分析，并生成了四份详细的技术文档。该项目是一个长期本科研究项目，目标是构建和评估能够预测跨域技术趋势的自设计智能体。

### 核心发现

1. **架构设计清晰**：项目采用三层分离（Resources、Data、Attempt），确保资源、数据、代码各司其职
2. **模块化设计完善**：Shared 模块提供稳定接口，支持多个实验类别复用
3. **数据流转规范**：Raw → Interim → Processed，每个阶段有明确的职责
4. **Agent 框架成熟**：BaseAgent 接口清晰，DataCollectionAgent 和 DataAnalysisAgent 已实现
5. **多源数据集成**：集成 OpenAlex、GDELT、GitHub 三个数据源
6. **实验管理规范**：版本化管理（_00, _01, _02），完整的元数据记录

---

## 生成的文档

### 1. TECHNOLOGY_FRAMEWORK_SUMMARY.md
**完整的技术框架总结文档**

- **规模**：23,061 字，719 行
- **覆盖范围**：
  - 项目整体架构（三层目录结构）
  - 数据流转管道（5 个阶段）
  - 核心模块架构（Shared、Agents、DataCollectors、Tools、Processors）
  - Agent 框架详解（BaseAgent、DataCollectionAgent、DataAnalysisAgent）
  - 数据采集客户端（OpenAlex、GDELT、GitHub）
  - 配置管理系统（PipelineConfig、TopicConfig）
  - 实验组织结构（5 个分类）
  - 基线实验示例（2026-08-14_simple_baseline）
  - 环境与依赖（Python 3.11+，10 个核心依赖）
  - 数据源与 API（详细的 API 文档）
  - 工作流与最佳实践（8 个设计规则）
  - 关键设计决策（5 个重要决策）
  - 扩展方向（4 个研究方向）
  - 快速参考和常见错误排查

**适用场景**：需要深入理解整个系统的人员（架构师、高级开发者、研究员）

---

### 2. ARCHITECTURE_DIAGRAM.md
**可视化架构图和流程图**

- **规模**：32,175 字，735 行
- **包含内容**：
  - 12 个 ASCII 架构图
  - 整体系统架构图
  - 数据流转管道图
  - Shared 模块架构图
  - Agent 框架结构图
  - 数据采集客户端架构图
  - 处理器架构图
  - 实验组织结构图
  - 基线实验流程图（4 个阶段）
  - 时间序列切分示意图
  - 配置驱动的参数流图
  - API 缓存机制图
  - 数据质量检查流程图
  - 模块依赖关系图
  - 错误处理与恢复图
  - 扩展点说明
  - 关键路径和性能估计

**适用场景**：需要快速理解系统流程和架构的人员（开发者、项目经理）

---

### 3. QUICK_REFERENCE.md
**快速参考卡**

- **规模**：10,087 字，407 行
- **内容类型**：
  - 项目概览（表格）
  - 目录结构速查
  - 核心模块速查（表格）
  - 数据源速查（3 个 API）
  - 配置文件速查（3 个配置文件）
  - 常用命令（8 个命令）
  - 常用代码片段（6 个片段）
  - 数据流转速查
  - 文件命名约定（表格）
  - 环境变量配置
  - 常见错误排查（5 个常见错误）
  - 关键路径和性能估计
  - 修改前检查清单（8 项）
  - 设计规则速记（7 条）
  - 实验 README 必答问题（5 个问题）
  - 有用的链接（表格）

**适用场景**：日常开发工作中需要快速查找信息的人员（开发者、研究员）

---

### 4. DOCUMENTATION_INDEX.md
**文档索引和导航**

- **规模**：9,532 字，340 行
- **功能**：
  - 文档总览和分类
  - 文档关系图
  - 快速导航（"我想..."问题解答）
  - 文档统计表
  - 按主题查找指南
  - 使用建议
  - 文档维护指南
  - 常见问题解答

**适用场景**：首次使用项目或需要找到相关文档的人员

---

## 项目技术框架概览

### 三层架构

```
Resources/          # 外部资料、论文、文档
    ↓
Data/              # 数据流转：Raw → Interim → Processed
    ↓
Attempt/           # 代码、实验、配置、环境
```

### 数据流转（5 个阶段）

```
Phase 1: Collection
  OpenAlex, GDELT, GitHub API
  ↓
Phase 2: Normalization
  DataCollectionAgent
  ↓
Phase 3: Analysis & Merge
  DataAnalysisAgent
  ↓
Phase 4: Processing
  Processors (normalize, quality_check)
  ↓
Phase 5: Reporting
  Reports (JSON, metrics)
```

### 核心模块

| 模块 | 文件 | 功能 |
|------|------|------|
| **config** | config.py | 配置加载、路径管理 |
| **agents** | base_agent.py | Agent 接口 |
| | data_collection_agent.py | 数据采集编排 |
| | data_analysis_agent.py | 数据合并、质量检查 |
| **data_collectors** | openalex_client.py | OpenAlex API |
| | gdelt_client.py | GDELT API |
| **tools** | search_tool.py | 统一搜索接口 |
| | github_client.py | GitHub API |
| **processors** | normalize.py | JSONL I/O、合并、透视 |
| | quality_checker.py | 数据质量检查 |

### 实验分类

- **Baselines/**：简单基线、传统方法、对照实验
- **Memory_Design/**：记忆结构、上下文管理实验
- **Reasoning_Architecture/**：推理链路、规划、工具调用实验
- **Reproduction/**：复现论文、开源项目实验
- **Sandbox/**：短期探索、尚未分类的工作

### 数据源

| 源 | API | 速率限制 | 缓存 |
|----|-----|---------|------|
| **OpenAlex** | Works API | 3 秒/请求 | SHA256 |
| **GDELT** | DOC 2.0 API | 10 秒/请求 | SHA256 |
| **GitHub** | REST API | 0.4-1.5 秒/请求 | SHA256 |

### 配置系统

- **default.yaml**：项目级配置（时区、随机种子、数据根目录）
- **topics.yaml**：主题定义（5 个主题：LLM、AI Agent、Robotics、Quantum、Edge）
- **sources.yaml**：数据源开关和参数

---

## 关键特性

### 1. 清晰的架构设计
- 三层分离（Resources、Data、Attempt）
- 模块化设计（Shared 模块提供稳定接口）
- 关注点分离（采集 ≠ 存储 ≠ 预处理 ≠ 评分 ≠ 预测 ≠ 报告）

### 2. 完善的数据管理
- 原始数据保留（Raw 层只追加，不覆盖）
- 中间数据隔离（Interim 层用于清洗中的数据）
- 版本化管理（_00, _01, _02）
- 完整的元数据记录

### 3. 成熟的 Agent 框架
- BaseAgent 接口清晰
- DataCollectionAgent 实现多源采集编排
- DataAnalysisAgent 实现数据合并和质量检查
- AgentResult 数据类统一返回格式

### 4. 多源数据集成
- OpenAlex：学术论文活动信号
- GDELT：新闻/行业活动信号
- GitHub：开源项目活动信号

### 5. 智能缓存机制
- 避免重复 API 调用
- 支持离线开发
- 确保可复现性

### 6. 规范的实验管理
- 版本化管理
- 完整的 README 模板
- 精确的运行命令记录
- 详细的结果报告

### 7. 完善的工作流程
- 修改前检查清单
- 设计规则和最佳实践
- 错误处理和恢复机制
- 验证和报告规范

---

## 基线实验示例

### 2026-08-14_simple_baseline

**目标**：打通完整的数据采集 → 标准化 → 预测 → 评估链路

**方法**：
- 移动平均（MA）：最近 3 个月的平均值
- 线性回归（LR）：时间序列拟合

**流程**：
1. **Phase 1**：从 OpenAlex 和 GDELT 采集数据
2. **Phase 2**：标准化和合并数据
3. **Phase 3**：使用 MA 和 LR 进行预测
4. **Phase 4**：计算 MAE、MAPE、RMSE 评估指标

**输出**：
- `collection_report.json`：采集统计
- `baseline_results.json`：详细预测结果
- `baseline_evaluations.json`：评估指标
- `summary.json`：汇总指标

---

## 技术栈

### 编程语言
- **Python**：3.11+

### 核心依赖
- **numpy**：数值计算
- **pandas**：数据处理
- **pydantic**：数据验证
- **pyyaml**：配置解析
- **requests**：HTTP 请求
- **scikit-learn**：机器学习
- **pytest**：测试框架
- **ruff**：代码检查

### 数据格式
- **JSONL**：行式 JSON（支持嵌套数据、流式处理）
- **YAML**：配置文件（人类可读）
- **JSON**：报告和缓存

---

## 工作流程

### 修改前检查清单
1. ✅ 检查完整的相关目录结构
2. ✅ 阅读 README.md 和相关文档
3. ✅ 追踪代码的调用者、输入、输出、配置、数据流
4. ✅ 总结当前架构、提议改动、影响文件、风险、验证计划
5. ✅ 对于架构改动、新依赖、新数据源，请求用户审查

### 设计规则
1. **分离关注点**：采集 ≠ 存储 ≠ 预处理 ≠ 评分 ≠ 预测 ≠ 报告
2. **复用接口**：优先使用现有工具，避免重复抽象
3. **参数外部化**：模型名、API 端点、提示、阈值都不硬编码
4. **清晰签名**：明确的输入、输出、副作用、失败行为
5. **保护密钥**：不提交 API 密钥、密码、访问令牌
6. **透明性**：每个非平凡的决策都要文档化
7. **可复现性**：版本化管理、完整元数据、精确命令

---

## 扩展方向

### 1. Memory_Design
- 长期记忆结构
- 上下文管理
- 记忆压缩

### 2. Reasoning_Architecture
- 推理链路
- 工具调用
- 规划和假设验证

### 3. Reproduction
- 复现已发表的预测方法
- 对照实验

### 4. Baselines
- 更强的统计方法（ARIMA、Prophet）
- 传统机器学习（随机森林、梯度提升）
- 简单启发式规则

---

## 常见命令

```powershell
# 激活虚拟环境
cd 'F:\Predictive agents\Attempt'
.\.venv\Scripts\Activate.ps1

# 运行基线实验
python -m Baselines.experiments.2026-08-14_simple_baseline.src.pipeline

# 运行测试
pytest tests/

# 代码检查
ruff check .
```

---

## 常见错误排查

| 错误 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: No module named 'config'` | sys.path 未包含 Shared/src | 在脚本顶部添加 sys.path.insert(0, ...) |
| `FileNotFoundError: .env` | 环境变量文件不存在 | 复制 `.env.example` 为 `.env` |
| `429 Too Many Requests` | API 速率限制 | 等待重试退避或检查缓存 |
| `pivot_table_extended.jsonl` 为空 | 数据采集失败 | 检查 `collection_report.json` 中的错误 |

---

## 文档使用指南

### 首次使用项目
1. 阅读 `README.md`（项目总览）
2. 阅读 `AGENTS.md`（工作协议）
3. 浏览 `ARCHITECTURE_DIAGRAM.md`（理解流程）
4. 保存 `QUICK_REFERENCE.md`（日常查找）

### 日常开发
1. 使用 `QUICK_REFERENCE.md` 快速查找命令和代码片段
2. 遇到问题时查看"常见错误排查"
3. 修改代码前检查"修改前检查清单"

### 深入学习
1. 阅读 `TECHNOLOGY_FRAMEWORK_SUMMARY.md` 的相关章节
2. 查看 `ARCHITECTURE_DIAGRAM.md` 的流程图
3. 阅读源代码注释和文档字符串

---

## 项目统计

### 代码规模
- **Shared 模块**：~1,000 行代码
- **基线实验**：~500 行代码
- **测试代码**：~300 行代码
- **总计**：~1,800 行代码

### 数据源
- **OpenAlex**：学术论文活动（1 个 API 调用）
- **GDELT**：新闻活动（1 个 API 调用）
- **GitHub**：开源项目活动（2 个搜索窗口）

### 主题数量
- **当前**：5 个主题（LLM、AI Agent、Robotics、Quantum、Edge）
- **可扩展**：无限制

### 时间范围
- **当前**：2023-01 至 2025-07（31 个月）
- **可配置**：任意时间范围

---

## 性能估计

### 数据采集耗时

| 场景 | 耗时 |
|------|------|
| 仅缓存 | < 5 秒 |
| 新采集（5 主题） | 70-75 秒 |
| 首次运行 | 1-2 分钟 |

### 数据规模

| 数据 | 规模 |
|------|------|
| 单个主题的月度记录 | 3 条（OpenAlex + GDELT + GitHub） |
| 5 个主题 × 31 个月 | 465 条记录 |
| 透视表 | 155 行（每个月份一行） |

---

## 下一步建议

### 短期（1-2 周）
1. ✅ 完成基线实验的首次运行
2. ✅ 验证数据采集的正确性
3. ✅ 检查数据质量报告

### 中期（1-2 个月）
1. 设计 Memory_Design 实验
2. 实现简单的记忆结构
3. 进行初步的记忆有效性评估

### 长期（3-6 个月）
1. 设计 Reasoning_Architecture 实验
2. 实现多步推理链路
3. 集成工具调用机制
4. 进行完整的 Agent 评估

---

## 总结

**预测智能体项目**是一个设计精良的研究项目框架，具有以下优势：

1. **架构清晰**：三层分离、模块化设计、关注点分离
2. **规范完善**：工作协议、设计规则、验证规范
3. **可复现性强**：版本化管理、完整元数据、精确命令
4. **易于扩展**：清晰的接口、配置驱动、模块化设计
5. **文档齐全**：四份详细的技术文档，覆盖所有方面

通过这个框架，研究者可以：
- 快速迭代实验（新增主题、数据源、模型）
- 可靠复现结果（配置 + 代码 + 数据 + 环境）
- 安全管理密钥和敏感数据
- 协作开发（清晰的职责边界、文档化的接口）

---

## 附录：文档清单

### 新生成的文档

| 文件名 | 大小 | 行数 | 用途 |
|--------|------|------|------|
| TECHNOLOGY_FRAMEWORK_SUMMARY.md | 23 KB | 719 | 完整技术框架 |
| ARCHITECTURE_DIAGRAM.md | 32 KB | 735 | 可视化架构 |
| QUICK_REFERENCE.md | 10 KB | 407 | 快速参考 |
| DOCUMENTATION_INDEX.md | 9.5 KB | 340 | 文档索引 |
| SUMMARY_REPORT.md | 本文件 | - | 总结报告 |

### 项目原始文档

| 文件名 | 位置 | 用途 |
|--------|------|------|
| README.md | 项目根目录 | 项目总览 |
| AGENTS.md | 项目根目录 | 工作协议 |
| Attempt/README.md | Attempt/ | 实验组织 |
| Data/README.md | Data/ | 数据规范 |
| Resources/README.md | Resources/ | 资源规范 |

---

**报告生成时间**：2026-08-17  
**项目根目录**：`F:\Predictive agents`  
**报告版本**：1.0  
**维护者**：Predictive Agents 研究团队
