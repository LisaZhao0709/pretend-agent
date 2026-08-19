# 预测智能体项目 - 技术框架总结

**项目根目录**：`F:\Predictive agents`  
**项目类型**：长期本科研究项目  
**核心目标**：构建和评估自设计的智能体，用于预测跨域技术趋势

---

## 一、项目整体架构

### 1.1 三层目录结构

```
F:\Predictive agents/
├── Resources/          # 外部资料、论文、文档、历史进展
├── Data/              # 数据流转（Raw → Interim → Processed）+ 报告
└── Attempt/           # 所有代码、实验、配置、环境
```

**设计理念**：严格分离数据、资源、代码，避免混淆；每个实验版本化管理，保证可复现性。

---

## 二、数据流转管道（Data Pipeline）

### 2.1 数据分层

```
Raw/                    # 原始 API 响应、爬虫数据（只追加，不覆盖）
  ├── APIs/            # OpenAlex、GDELT、GitHub 原始缓存
  └── Crawler/         # 爬虫数据
  
Interim/               # 清洗中的中间数据
  ├── openalex_records.jsonl
  ├── gdelt_records.jsonl
  └── github_signals_YYYY-MM-DD.jsonl

Processed/             # 可直接消费的版本化数据
  └── pivot_table_extended.jsonl

Reports/               # 质量报告、分析报告、预测结果
  ├── collection_report.json
  ├── quality_report.json
  ├── baseline_results.json
  └── summary.json

Metadata/              # 数据源信息、采集时间、许可、处理历史
Schemas/               # JSON Schema、字段定义、校验规则
```

### 2.2 数据命名约定

- 格式：`source_topic_YYYY-MM-DD_vXXX.jsonl`
- 版本号：`_00`, `_01`, `_02`（不覆盖历史版本）
- 日期格式：`YYYY-MM-DD`（可排序）

---

## 三、核心模块架构

### 3.1 Shared（共享模块）

所有实验类别共用的稳定接口，位于 `Attempt/Shared/src/`

```
Shared/src/
├── config.py                    # 配置加载、路径管理
├── agents/
│   ├── base_agent.py           # BaseAgent 接口 + AgentResult 数据类
│   ├── data_collection_agent.py # 多源数据采集编排
│   └── data_analysis_agent.py   # 数据合并、质量检查
├── data_collectors/
│   ├── openalex_client.py       # OpenAlex Works API 客户端
│   ├── gdelt_client.py          # GDELT DOC 2.0 API 客户端
│   └── __init__.py
├── tools/
│   ├── search_tool.py           # 统一搜索接口（路由到不同源）
│   ├── github_client.py         # GitHub REST API 客户端
│   └── __init__.py
└── processors/
    ├── normalize.py             # 数据标准化、JSONL 序列化
    ├── quality_checker.py       # 数据质量检查
    └── __init__.py
```

#### 3.1.1 Agent 框架

**BaseAgent 接口**
```python
class BaseAgent:
    def run(self) -> AgentResult:
        raise NotImplementedError

@dataclass
class AgentResult:
    ok: bool
    detail: dict[str, Any]  # 结果或错误信息
```

**DataCollectionAgent**
- 迭代主题和启用的数据源
- 使用 SearchTool 采集数据
- 输出 `collection_report.json`

**DataAnalysisAgent**
- 加载采集的记录（OpenAlex、GDELT、GitHub）
- 合并并创建透视表
- 运行质量检查
- 输出 `pivot_table_extended.jsonl` 和 `quality_report.json`

#### 3.1.2 数据采集客户端

**OpenAlex Works API**
- 使用 `group_by=publication_date` 单次请求获取所有日期计数
- 本地聚合到月度窗口
- 缓存机制：SHA256(url+params) → JSON
- 速率限制：3 秒/请求，429 错误重试（指数退避）

**GDELT DOC 2.0 API**
- 单次时间线请求最小化 API 调用
- 本地拆分为月度窗口
- 缓存机制同上
- 速率限制：10 秒/请求

**GitHub REST API**
- 两个搜索窗口：
  1. `created:>=D-7` 排序 by stars（新仓库）
  2. `pushed:>=D-1` 排序 by stars（活跃仓库）
- 支持可选认证（GITHUB_TOKEN）
- 每页 30 条，最多 4 页
- 认证用户：0.4 秒/请求；非认证：1.5 秒/请求

#### 3.1.3 数据处理器

**normalize.py**
- `save_records_to_jsonl()`：记录列表 → JSONL 文件
- `load_jsonl()`：JSONL 文件 → 记录列表
- `merge_records_by_source()`：合并 OpenAlex + GDELT
- `build_feature_matrix()`：按主题分组
- `create_pivot_table()`：透视（每行一个窗口，包含多源计数）

**quality_checker.py**
- 检查缺失值、异常值、覆盖范围
- 生成质量评分和详细报告

#### 3.1.4 配置管理

**config.py**
```python
@dataclass
class TopicConfig:
    topic_id: str
    topic_label: str
    openalex_query: str
    gdelt_query: str

@dataclass
class PipelineConfig:
    project_name: str
    timezone: str
    random_seed: int
    data_root: Path
    resources_root: Path
    dataset_name: str
    start_date: str  # YYYY-MM
    end_date: str    # YYYY-MM
    window_size_months: int
    train_ratio: float
    validation_ratio: float
    test_ratio: float
    topics: list[TopicConfig]
    
    # 属性：自动生成路径
    @property
    def raw_api_path(self) -> Path: ...
    @property
    def interim_path(self) -> Path: ...
    @property
    def processed_path(self) -> Path: ...
    @property
    def reports_path(self) -> Path: ...
```

**配置文件**
- `configs/default.yaml`：项目级配置（时区、随机种子、数据根目录）
- `configs/topics.yaml`：主题定义（ID、标签、查询语句）
- `configs/sources.yaml`：数据源开关和参数（GitHub k_new、k_active 等）

---

## 四、实验组织结构

### 4.1 实验分类

```
Attempt/
├── Memory_Design/           # 记忆结构、上下文管理实验
├── Reasoning_Architecture/  # 推理链路、规划、工具调用实验
├── Reproduction/            # 复现论文/开源项目实验
├── Baselines/              # 简单基线、传统方法、对照实验
├── Sandbox/                # 短期探索、尚未分类的工作
├── Shared/                 # 共享模块（见上文）
├── scripts/                # 环境、数据检查脚本
├── notebooks/              # 探索性 Jupyter 笔记本
├── configs/                # 跨实验公共配置
└── docs/                   # 架构图、设计说明
```

### 4.2 单次实验最小结构

```
experiments/YYYY-MM-DD_short_name/
├── README.md               # 中文实验说明、假设、结果、下一步
├── src/                    # 可复用代码
│   ├── pipeline.py        # 主入口
│   ├── model.py           # 模型/方法实现
│   ├── evaluator.py       # 评估逻辑
│   └── report_generator.py # 报告生成
├── tests/                  # 最小验证和回归测试
├── configs/                # 参数、数据版本、运行配置
└── docs/                   # 额外设计说明
```

### 4.3 实验 README 必答问题

1. **这次尝试想验证什么？**
2. **使用了哪个数据版本和哪些外部资料？**
3. **如何安装和运行？**（精确命令）
4. **结果是什么，指标如何解释？**
5. **哪些假设失败了，下一步是什么？**

---

## 五、基线实验示例（2026-08-14_simple_baseline）

### 5.1 目标

打通"数据采集 → 标准化 → 基线预测 → 评估"的完整链路。

### 5.2 方法

- **移动平均**（MA）：最近 3 个月的平均值
- **线性回归**（LR）：时间序列拟合

### 5.3 流程

```
Phase 1: Data Collection
  ├─ OpenAlex：按主题查询，按月聚合
  ├─ GDELT：按主题查询，按月聚合
  └─ 输出：openalex_records.jsonl, gdelt_records.jsonl

Phase 2: Data Normalization
  ├─ 加载 JSONL 记录
  ├─ 合并多源数据
  ├─ 创建透视表（每行一个月，包含多源计数）
  └─ 输出：pivot_table_extended.jsonl

Phase 3: Baseline Forecasting
  ├─ 按主题分组
  ├─ 按 70/30 时间切分（训练/测试）
  ├─ 逐月滚动预测（MA 和 LR）
  └─ 输出：baseline_results.json

Phase 4: Evaluation
  ├─ 计算 MAE、MAPE、RMSE
  ├─ 生成评估指标
  └─ 输出：baseline_evaluations.json, summary.json
```

### 5.4 关键代码

**baseline_model.py**
```python
def moving_average_forecast(history: list[float], window: int = 3) -> float:
    """简单移动平均"""
    
def linear_regression_forecast(history: list[float]) -> float:
    """线性回归预测"""
    
def forecast_topic(pivot_rows, column, method, window, train_ratio) -> dict:
    """按主题预测，返回结果和指标"""
```

**evaluator.py**
- `evaluate_forecast()`：计算 MAE、MAPE、RMSE
- `summarize_results()`：汇总所有主题的指标

**report_generator.py**
- 生成 JSON 报告（结果、评估、汇总）

### 5.5 运行命令

```powershell
cd 'F:\Predictive agents\Attempt'
.\.venv\Scripts\Activate.ps1
python -m Baselines.experiments.2026-08-14_simple_baseline.src.pipeline
```

### 5.6 输出

```
Data/Reports/technology_cultivation_00/
├── collection_report.json      # 采集统计
├── baseline_results.json       # 详细预测结果
├── baseline_evaluations.json   # 评估指标
└── summary.json               # 汇总指标
```

---

## 六、环境与依赖

### 6.1 Python 版本

- **要求**：Python >= 3.11
- **虚拟环境**：`Attempt/.venv/`（已加入 .gitignore）

### 6.2 核心依赖

```
numpy>=1.26              # 数值计算
pandas>=2.2              # 数据处理
pydantic>=2.7            # 数据验证
python-dotenv>=1.0       # 环境变量加载
pyyaml>=6.0              # YAML 配置解析
requests>=2.32           # HTTP 请求
httpx>=0.27              # 异步 HTTP（备选）
scikit-learn>=1.5        # 机器学习（线性回归等）
pytest>=8.2              # 测试框架
```

### 6.3 配置文件

- **pyproject.toml**：项目元数据、依赖声明、pytest 配置
- **requirements.txt**：锁定版本的依赖列表
- **environment.yml**：Conda 环境定义（可选）
- **.env.example**：环境变量模板（不提交密钥）
- **.env**：本地环境变量（Git 忽略）

---

## 七、数据源与 API

### 7.1 OpenAlex

- **API**：`https://api.openalex.org/works`
- **查询方式**：按出版日期分组（`group_by=publication_date`）
- **速率限制**：3 秒/请求
- **缓存**：SHA256(url+params) → JSON 文件
- **重试**：429 错误，指数退避（最多 5 次）

### 7.2 GDELT DOC 2.0

- **API**：`https://api.gdeltproject.org/api/v2/doc/doc`
- **查询方式**：时间线请求（单次获取日期范围内的所有数据）
- **速率限制**：10 秒/请求
- **缓存**：同上
- **重试**：最多 3 次，15 秒退避

### 7.3 GitHub

- **API**：`https://api.github.com/search/repositories`
- **认证**：可选 GITHUB_TOKEN（Fine-grained PAT 或 OAuth）
- **速率限制**：
  - 认证：6000 请求/小时（0.4 秒/请求）
  - 非认证：60 请求/小时（1.5 秒/请求）
- **搜索窗口**：
  - 新仓库：`created:>=D-7` 排序 by stars（Top-K 100）
  - 活跃仓库：`pushed:>=D-1` 排序 by stars（Top-K 50）

---

## 八、主题与查询配置

### 8.1 当前主题（topics.yaml）

| 主题 ID | 标签 | OpenAlex 查询 | GDELT 查询 |
|---------|------|--------------|-----------|
| llm | Large Language Models | large language model | "large language model" |
| ai_agent | AI Agents | AI agent autonomous | "AI agent" |
| robotics | Robotics | robotics manipulation | robotics |
| quantum_comp | Quantum Computing | quantum computing | "quantum computing" |
| edge_comp | Edge Computing | edge computing | "edge computing" |

### 8.2 数据源开关（sources.yaml）

```yaml
sources:
  openalex:
    enabled: true
  gdelt:
    enabled: true
  github:
    enabled: true
    k_new: 100              # 新仓库 Top-K
    k_active: 50            # 活跃仓库 Top-K
    delta_7d_threshold: 100 # 7 天星标增长阈值
    use_llm_summarize: false
    language_whitelist: []  # 可选语言过滤
    org_whitelist: []       # 可选组织过滤
```

---

## 九、工作流与最佳实践

### 9.1 修改前检查清单

1. ✅ 检查完整的相关目录结构
2. ✅ 阅读 `README.md` 和相关文档
3. ✅ 追踪代码的调用者、输入、输出、配置、数据流
4. ✅ 总结当前架构、提议改动、影响文件、风险、验证计划
5. ✅ 对于架构改动、新依赖、新数据源、公开接口改动，请求用户审查

### 9.2 设计规则

1. **分离关注点**：数据采集 ≠ 存储 ≠ 预处理 ≠ 评分 ≠ 预测 ≠ 报告
2. **复用接口**：优先使用现有工具和实用程序，避免重复抽象
3. **参数外部化**：模型名、API 端点、提示、阈值、时间窗口、文件路径都不硬编码
4. **清晰的函数签名**：明确的输入、输出、副作用、失败行为、职责范围
5. **保护密钥**：不提交 API 密钥、密码、访问令牌、未脱敏数据
6. **透明性**：每个非平凡的评分或预测决策都要文档化

### 9.3 版本管理

- **实验版本**：`_00`, `_01`, `_02`（不覆盖）
- **稳定文件**：`README.md`, `.gitignore`, `AGENTS.md`, 环境定义文件（Git 记录历史）
- **重大改动前**：创建 Git 检查点，提交有意义的、可复现的状态

### 9.4 数据完整性

1. **记录元数据**：源 URL/API、采集时间、查询参数、许可、模式、处理步骤
2. **保留原始数据**：衍生数据单独存储，记录转换过程
3. **分离观察和解释**：不将 LLM 生成的声明作为证据，必须有可追踪的来源
4. **说明不确定性**：缺失数据、选择偏差、已知限制

### 9.5 验证与报告

修改代码后：
1. 运行最小相关测试或验证脚本
2. 检查格式、导入、配置加载、数据路径
3. 报告改动文件、执行命令、结果、警告、未解决问题、建议下一步
4. 无法运行验证时，解释原因而非声称成功

---

## 十、文件树概览

```
F:\Predictive agents/
├── README.md                          # 项目总览、推荐工作流
├── AGENTS.md                          # 工作协议、设计规则、验证规范
├── TECHNOLOGY_FRAMEWORK_SUMMARY.md    # 本文档
│
├── Resources/
│   ├── README.md
│   ├── Papers/                        # 论文、预印本
│   ├── Documentation/                 # 官方文档、API 文档
│   ├── Project_Introductions/         # 开源项目介绍
│   ├── Historical_Progress/           # 阶段总结、决策记录
│   └── Notes/                         # 阅读笔记、综述
│
├── Data/
│   ├── README.md
│   ├── Raw/
│   │   ├── APIs/
│   │   │   └── technology_cultivation_00/
│   │   │       ├── openalex/
│   │   │       ├── gdelt/
│   │   │       └── github/
│   │   └── Crawler/
│   ├── Interim/technology_cultivation_00/
│   │   ├── openalex_records.jsonl
│   │   ├── gdelt_records.jsonl
│   │   └── github_signals_YYYY-MM-DD.jsonl
│   ├── Processed/technology_cultivation_00/
│   │   └── pivot_table_extended.jsonl
│   ├── Reports/technology_cultivation_00/
│   │   ├── collection_report.json
│   │   ├── quality_report.json
│   │   ├── baseline_results.json
│   │   └── summary.json
│   ├── Metadata/
│   ├── Schemas/
│   └── Cache/
│
└── Attempt/
    ├── README.md
    ├── pyproject.toml
    ├── requirements.txt
    ├── environment.yml
    ├── .env.example
    ├── .env                           # Git 忽略
    ├── .venv/                         # Git 忽略
    │
    ├── Shared/                        # 共享模块
    │   └── src/
    │       ├── config.py
    │       ├── agents/
    │       │   ├── base_agent.py
    │       │   ├── data_collection_agent.py
    │       │   └── data_analysis_agent.py
    │       ├── data_collectors/
    │       │   ├── openalex_client.py
    │       │   └── gdelt_client.py
    │       ├── tools/
    │       │   ├── search_tool.py
    │       │   └── github_client.py
    │       └── processors/
    │           ├── normalize.py
    │           └── quality_checker.py
    │
    ├── Baselines/
    │   ├── README.md
    │   ├── experiments/
    │   │   ├── 2026-08-14_simple_baseline/
    │   │   │   ├── README.md
    │   │   │   └── src/
    │   │   │       ├── pipeline.py
    │   │   │       ├── baseline_model.py
    │   │   │       ├── evaluator.py
    │   │   │       ├── report_generator.py
    │   │   │       └── test_*.py
    │   │   └── technology_cultivation_forecast_00/
    │   ├── src/
    │   ├── tests/
    │   └── configs/
    │
    ├── Memory_Design/
    │   ├── README.md
    │   ├── experiments/
    │   ├── src/
    │   ├── tests/
    │   ├── configs/
    │   └── docs/
    │
    ├── Reasoning_Architecture/
    │   ├── README.md
    │   ├── experiments/
    │   ├── src/
    │   ├── tests/
    │   ├── configs/
    │   └── docs/
    │
    ├── Reproduction/
    │   ├── README.md
    │   ├── experiments/
    │   ├── src/
    │   ├── tests/
    │   ├── configs/
    │   └── docs/
    │
    ├── Sandbox/
    │   ├── README.md
    │   └── ...
    │
    ├── scripts/
    │   └── ...
    │
    ├── notebooks/
    │   ├── README.md
    │   └── 1.0.ipynb
    │
    ├── configs/
    │   ├── default.yaml
    │   ├── topics.yaml
    │   ├── sources.yaml
    │   └── README.md
    │
    ├── docs/
    │   └── experiment_review_template.md
    │
    └── _template/
        ├── README.md
        ├── src/
        ├── tests/
        ├── configs/
        └── docs/
```

---

## 十一、关键设计决策

### 11.1 为什么分离 Shared？

- **稳定接口**：多个实验类别共用的工具（数据加载、API 客户端、处理器）
- **最小测试**：共用代码需要基础验证，避免实验间的隐藏依赖
- **版本控制**：Shared 的改动影响所有实验，需要谨慎评估

### 11.2 为什么使用 YAML 配置？

- **人类可读**：非技术人员也能理解和修改
- **版本控制友好**：易于 Git diff 和 review
- **参数灵活性**：实验参数不硬编码，支持快速迭代

### 11.3 为什么缓存 API 响应？

- **成本控制**：避免重复调用 API（特别是 OpenAlex、GDELT 的大查询）
- **可复现性**：相同的查询总是返回相同的结果（即使 API 更新）
- **离线开发**：网络不可用时仍可继续工作

### 11.4 为什么使用 JSONL 而非 CSV？

- **嵌套数据**：支持 `features` 等复杂字段
- **流式处理**：逐行读写，内存高效
- **灵活模式**：不同记录可有不同字段

### 11.5 为什么分离 Agent 和 Model？

- **Agent**：编排、数据流、错误处理（Shared）
- **Model**：具体算法、评估逻辑（实验特定）
- **好处**：Agent 框架稳定，Model 可快速迭代

---

## 十二、扩展方向

### 12.1 Memory_Design

- 长期记忆结构（如何存储历史预测、反馈）
- 上下文管理（如何在有限的 token 预算内选择相关信息）
- 记忆压缩（如何总结长期观察）

### 12.2 Reasoning_Architecture

- 推理链路（如何从数据到预测）
- 工具调用（Agent 如何决定使用哪个数据源）
- 规划（多步推理、假设验证）

### 12.3 Reproduction

- 复现已发表的预测方法
- 对照实验（Agent 方法 vs. 统计基线）

### 12.4 Baselines

- 更强的统计方法（ARIMA、Prophet）
- 传统机器学习（随机森林、梯度提升）
- 简单启发式规则

---

## 十三、快速参考

### 13.1 常用命令

```powershell
# 激活虚拟环境
cd 'F:\Predictive agents\Attempt'
.\.venv\Scripts\Activate.ps1

# 运行基线实验
python -m Baselines.experiments.2026-08-14_simple_baseline.src.pipeline

# 运行测试
pytest tests/
pytest Memory_Design/tests/
pytest Reasoning_Architecture/tests/

# 检查代码风格
ruff check .

# 安装新依赖
pip install package_name
# 然后更新 requirements.txt
pip freeze > requirements.txt
```

### 13.2 常见路径

```python
# 在代码中获取项目根目录
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # Attempt/Shared/src/... → 项目根
ATTEMPT_ROOT = Path(__file__).resolve().parents[2]  # Attempt/Shared/src/... → Attempt

# 加载配置
from config import load_pipeline_config
cfg = load_pipeline_config()
print(cfg.raw_api_path)      # F:\Predictive agents\Data\Raw\APIs\technology_cultivation_00
print(cfg.interim_path)      # F:\Predictive agents\Data\Interim\technology_cultivation_00
print(cfg.processed_path)    # F:\Predictive agents\Data\Processed\technology_cultivation_00
print(cfg.reports_path)      # F:\Predictive agents\Data\Reports\technology_cultivation_00
```

### 13.3 常见错误排查

| 错误 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: No module named 'config'` | sys.path 未包含 Shared/src | 在脚本顶部添加 `sys.path.insert(0, str(ATTEMPT_ROOT / "Shared" / "src"))` |
| `FileNotFoundError: .env` | 环境变量文件不存在 | 复制 `.env.example` 为 `.env`，填入 API 密钥 |
| `429 Too Many Requests` | API 速率限制 | 等待重试退避时间，或检查缓存是否有效 |
| `pivot_table_extended.jsonl` 为空 | 数据采集失败 | 检查 `collection_report.json` 中的错误信息 |

---

## 十四、总结

**Predictive Agents** 是一个精心设计的研究项目框架，强调：

1. **清晰分离**：资源、数据、代码各司其职
2. **可复现性**：版本化管理、完整的元数据、精确的运行命令
3. **可扩展性**：共享模块、配置驱动、Agent 框架
4. **数据完整性**：原始数据保留、处理过程记录、质量检查
5. **工程规范**：稳定接口、最小测试、文档化决策

通过这个框架，研究者可以：
- 快速迭代实验（新增主题、数据源、模型）
- 可靠复现结果（配置 + 代码 + 数据 + 环境）
- 安全管理密钥和敏感数据
- 协作开发（清晰的职责边界、文档化的接口）

---

**文档生成时间**：2026-08-17  
**项目根目录**：`F:\Predictive agents`  
**维护者**：Predictive Agents 研究团队
