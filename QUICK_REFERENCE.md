# 预测智能体项目 - 快速参考卡

## 项目概览

| 项 | 值 |
|---|---|
| **项目名** | Predictive Agents |
| **类型** | 长期本科研究项目 |
| **目标** | 构建和评估预测跨域技术趋势的智能体 |
| **根目录** | `F:\Predictive agents` |
| **Python 版本** | >= 3.11 |
| **虚拟环境** | `Attempt/.venv/` |

---

## 目录结构速查

```
F:\Predictive agents/
├── Resources/          # 论文、文档、历史进展
├── Data/              # 数据流转：Raw → Interim → Processed
└── Attempt/           # 代码、实验、配置
    ├── Shared/        # 共享模块（稳定接口）
    ├── Baselines/     # 基线实验
    ├── Memory_Design/
    ├── Reasoning_Architecture/
    ├── Reproduction/
    ├── Sandbox/
    ├── scripts/
    ├── notebooks/
    ├── configs/       # default.yaml, topics.yaml, sources.yaml
    └── docs/
```

---

## 核心模块速查

### Shared/src/

| 模块 | 文件 | 功能 |
|------|------|------|
| **config** | `config.py` | 配置加载、路径管理 |
| **agents** | `base_agent.py` | BaseAgent 接口 |
| | `data_collection_agent.py` | 多源数据采集编排 |
| | `data_analysis_agent.py` | 数据合并、质量检查 |
| **data_collectors** | `openalex_client.py` | OpenAlex API 客户端 |
| | `gdelt_client.py` | GDELT API 客户端 |
| **tools** | `search_tool.py` | 统一搜索接口（路由器） |
| | `github_client.py` | GitHub API 客户端 |
| **processors** | `normalize.py` | JSONL I/O、合并、透视 |
| | `quality_checker.py` | 数据质量检查 |

---

## 数据源速查

### OpenAlex Works API

```
URL: https://api.openalex.org/works
方法: group_by=publication_date (单次请求获取所有日期计数)
速率限制: 3 秒/请求
重试: 429 错误，指数退避 (最多 5 次)
缓存: SHA256(url+params)[:16].json
```

### GDELT DOC 2.0 API

```
URL: https://api.gdeltproject.org/api/v2/doc/doc
方法: 时间线请求 (单次获取日期范围内所有数据)
速率限制: 10 秒/请求
重试: 最多 3 次，15 秒退避
缓存: SHA256(url+params)[:16].json
```

### GitHub REST API

```
URL: https://api.github.com/search/repositories
认证: 可选 GITHUB_TOKEN (Fine-grained PAT)
速率限制: 
  - 认证: 6000/小时 (0.4 秒/请求)
  - 非认证: 60/小时 (1.5 秒/请求)
搜索窗口:
  - 新仓库: created:>=D-7 (Top-K 100)
  - 活跃仓库: pushed:>=D-1 (Top-K 50)
```

---

## 配置文件速查

### default.yaml

```yaml
project_name: predictive-agents
timezone: Asia/Shanghai
random_seed: 42
data_root: F:\Predictive agents\Data
resources_root: F:\Predictive agents\Resources
default_data_split:
  train_ratio: 0.7
  validation_ratio: 0.15
  test_ratio: 0.15
```

### topics.yaml

```yaml
topics:
  - topic_id: llm
    topic_label: Large Language Models
    openalex_query: large language model
    gdelt_query: "large language model"
  # ... 更多主题
```

### sources.yaml

```yaml
sources:
  openalex:
    enabled: true
  gdelt:
    enabled: true
  github:
    enabled: true
    k_new: 100
    k_active: 50
    delta_7d_threshold: 100
    use_llm_summarize: false
    language_whitelist: []
    org_whitelist: []
```

---

## 常用命令

### 环境管理

```powershell
# 激活虚拟环境
cd 'F:\Predictive agents\Attempt'
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 更新依赖列表
pip freeze > requirements.txt

# 检查依赖
pip list
```

### 运行实验

```powershell
# 运行基线实验
python -m Baselines.experiments.2026-08-14_simple_baseline.src.pipeline

# 运行特定测试
pytest tests/
pytest Baselines/experiments/2026-08-14_simple_baseline/src/test_full_pipeline.py

# 运行所有测试
pytest
```

### 代码检查

```powershell
# 代码风格检查
ruff check .

# 格式化代码
ruff format .
```

---

## 常用代码片段

### 加载配置

```python
from config import load_pipeline_config

cfg = load_pipeline_config()
print(cfg.raw_api_path)      # F:\Predictive agents\Data\Raw\APIs\...
print(cfg.interim_path)      # F:\Predictive agents\Data\Interim\...
print(cfg.processed_path)    # F:\Predictive agents\Data\Processed\...
print(cfg.reports_path)      # F:\Predictive agents\Data\Reports\...
```

### 生成月度窗口

```python
from config import generate_monthly_windows

windows = generate_monthly_windows("2023-01", "2025-07")
# [("2023-01", "2023-02"), ("2023-02", "2023-03"), ...]
```

### 采集数据

```python
from data_collectors.openalex_client import collect_openalex_topic
from config import generate_monthly_windows

windows = generate_monthly_windows("2023-01", "2025-07")
records = collect_openalex_topic(
    topic_id="llm",
    topic_label="Large Language Models",
    query="large language model",
    windows=windows,
    cache_dir=Path("..."),
)
```

### 处理数据

```python
from processors.normalize import (
    load_jsonl,
    merge_records_by_source,
    create_pivot_table,
    save_records_to_jsonl,
)

openalex_recs = load_jsonl(Path("openalex_records.jsonl"))
gdelt_recs = load_jsonl(Path("gdelt_records.jsonl"))
merged = merge_records_by_source(openalex_recs, gdelt_recs)
pivot = create_pivot_table(merged)
save_records_to_jsonl(pivot, Path("pivot_table.jsonl"))
```

### 质量检查

```python
from processors.quality_checker import check_data_quality, save_quality_report

quality = check_data_quality(pivot)
save_quality_report(quality, Path("quality_report.json"))
print(f"Quality Score: {quality['overall_score']}")
```

---

## 数据流转速查

```
Phase 1: Collection
  OpenAlex, GDELT, GitHub API
  ↓
  Data/Raw/APIs/technology_cultivation_00/
  ├─ openalex/*.json (缓存)
  ├─ gdelt/*.json (缓存)
  └─ github/*.json (缓存)

Phase 2: Normalization
  DataCollectionAgent
  ↓
  Data/Interim/technology_cultivation_00/
  ├─ openalex_records.jsonl
  ├─ gdelt_records.jsonl
  └─ github_signals_YYYY-MM-DD.jsonl

Phase 3: Analysis & Merge
  DataAnalysisAgent
  ↓
  Data/Processed/technology_cultivation_00/
  └─ pivot_table_extended.jsonl

Phase 4: Forecasting & Evaluation
  Baseline Model, Evaluator
  ↓
  Data/Reports/technology_cultivation_00/
  ├─ collection_report.json
  ├─ quality_report.json
  ├─ baseline_results.json
  └─ summary.json
```

---

## 文件命名约定

| 类型 | 格式 | 例子 |
|------|------|------|
| **数据文件** | `source_topic_YYYY-MM-DD_vXXX.jsonl` | `openalex_llm_2026-08-14_v00.jsonl` |
| **实验目录** | `YYYY-MM-DD_short_name` | `2026-08-14_simple_baseline` |
| **版本号** | `_00`, `_01`, `_02` | (不覆盖历史版本) |
| **日期格式** | `YYYY-MM-DD` | `2026-08-17` |

---

## 环境变量 (.env)

```bash
# GitHub Token (可选)
GITHUB_TOKEN=github_pat_xxxxx

# OpenAlex Email (可选，用于礼貌池)
OPENALEX_EMAIL=research@example.com

# 其他 API 密钥...
```

**注意**：`.env` 文件已加入 `.gitignore`，不会提交到 Git。

---

## 常见错误排查

| 错误 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: No module named 'config'` | sys.path 未包含 Shared/src | 在脚本顶部添加 `sys.path.insert(0, str(ATTEMPT_ROOT / "Shared" / "src"))` |
| `FileNotFoundError: .env` | 环境变量文件不存在 | 复制 `.env.example` 为 `.env` |
| `429 Too Many Requests` | API 速率限制 | 等待重试退避，或检查缓存 |
| `pivot_table_extended.jsonl` 为空 | 数据采集失败 | 检查 `collection_report.json` 中的错误 |
| `Permission denied` | 文件权限问题 | 检查目录权限，或以管理员身份运行 |

---

## 关键路径

```
最快路径（仅缓存）:
  pipeline.py → 1-2 秒

完整路径（新采集，5 主题）:
  OpenAlex: 15 秒
  GDELT: 50 秒
  GitHub: 5-10 秒
  ─────────────────
  总计: 70-75 秒

首次运行: 1-2 分钟
```

---

## 修改前检查清单

- [ ] 检查完整的相关目录结构
- [ ] 阅读 `README.md` 和相关文档
- [ ] 追踪代码的调用者、输入、输出、配置、数据流
- [ ] 总结当前架构、提议改动、影响文件、风险、验证计划
- [ ] 对于架构改动、新依赖、新数据源，请求用户审查
- [ ] 修改后运行相关测试
- [ ] 检查格式、导入、配置加载、数据路径
- [ ] 报告改动文件、执行命令、结果、警告、下一步

---

## 设计规则速记

1. **分离关注点**：采集 ≠ 存储 ≠ 预处理 ≠ 评分 ≠ 预测 ≠ 报告
2. **复用接口**：优先使用现有工具，避免重复抽象
3. **参数外部化**：模型名、API 端点、提示、阈值都不硬编码
4. **清晰签名**：明确的输入、输出、副作用、失败行为
5. **保护密钥**：不提交 API 密钥、密码、访问令牌
6. **透明性**：每个非平凡的决策都要文档化
7. **可复现性**：版本化管理、完整元数据、精确命令

---

## 实验 README 必答问题

1. **这次尝试想验证什么？**
2. **使用了哪个数据版本和哪些外部资料？**
3. **如何安装和运行？**（精确命令）
4. **结果是什么，指标如何解释？**
5. **哪些假设失败了，下一步是什么？**

---

## 有用的链接

| 资源 | 位置 |
|------|------|
| **项目总览** | `F:\Predictive agents\README.md` |
| **工作协议** | `F:\Predictive agents\AGENTS.md` |
| **技术框架** | `F:\Predictive agents\TECHNOLOGY_FRAMEWORK_SUMMARY.md` |
| **架构图** | `F:\Predictive agents\ARCHITECTURE_DIAGRAM.md` |
| **快速参考** | `F:\Predictive agents\QUICK_REFERENCE.md` |
| **实验模板** | `F:\Predictive agents\Attempt\_template\README.md` |
| **基线实验** | `F:\Predictive agents\Attempt\Baselines\experiments\2026-08-14_simple_baseline\README.md` |

---

## 联系与支持

- **项目根目录**：`F:\Predictive agents`
- **虚拟环境**：`Attempt/.venv/`
- **配置文件**：`Attempt/configs/`
- **数据目录**：`Data/`
- **资源目录**：`Resources/`

---

**最后更新**：2026-08-17  
**版本**：1.0
