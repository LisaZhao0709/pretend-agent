# 预测智能体项目 - 架构图解

## 一、整体系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Predictive Agents System                          │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Resources/     │  │     Data/        │  │    Attempt/      │
│  (外部资料)      │  │   (数据流转)     │  │   (所有代码)     │
├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│ Papers/          │  │ Raw/             │  │ Shared/          │
│ Documentation/   │  │ Interim/         │  │ Baselines/       │
│ Project_Intro/   │  │ Processed/       │  │ Memory_Design/   │
│ Historical/      │  │ Reports/         │  │ Reasoning_Arch/  │
│ Notes/           │  │ Metadata/        │  │ Reproduction/    │
│                  │  │ Schemas/         │  │ Sandbox/         │
│                  │  │ Cache/           │  │ scripts/         │
│                  │  │                  │  │ notebooks/       │
│                  │  │                  │  │ configs/         │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 二、数据流转管道（Data Pipeline）

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Flow Pipeline                           │
└─────────────────────────────────────────────────────────────────────┘

                        ┌──────────────────┐
                        │  Topics Config   │
                        │  (topics.yaml)   │
                        └────────┬─────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │  OpenAlex    │  │    GDELT     │  │   GitHub     │
        │  Works API   │  │  DOC 2.0 API │  │  REST API    │
        └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
               │                 │                 │
        ┌──────▼─────────────────▼─────────────────▼──────┐
        │          Data Collection Agent                  │
        │  (Shared/src/agents/data_collection_agent.py)  │
        └──────┬─────────────────────────────────────────┘
               │
        ┌──────▼──────────────────────────────────────────┐
        │  Raw Data Storage (Data/Raw/APIs/...)           │
        │  ├─ openalex_records.jsonl (cached)             │
        │  ├─ gdelt_records.jsonl (cached)                │
        │  └─ github_signals_YYYY-MM-DD.jsonl (cached)    │
        └──────┬──────────────────────────────────────────┘
               │
        ┌──────▼──────────────────────────────────────────┐
        │          Data Analysis Agent                    │
        │  (Shared/src/agents/data_analysis_agent.py)    │
        │  ├─ Load & Merge Records                        │
        │  ├─ Create Pivot Table                          │
        │  └─ Quality Check                               │
        └──────┬──────────────────────────────────────────┘
               │
        ┌──────▼──────────────────────────────────────────┐
        │  Processed Data (Data/Processed/...)            │
        │  └─ pivot_table_extended.jsonl                  │
        │     (每行一个月份，包含多源计数)                │
        └──────┬──────────────────────────────────────────┘
               │
        ┌──────▼──────────────────────────────────────────┐
        │  Reports (Data/Reports/...)                     │
        │  ├─ collection_report.json                      │
        │  ├─ quality_report.json                         │
        │  ├─ baseline_results.json                       │
        │  └─ summary.json                                │
        └──────────────────────────────────────────────────┘
```

---

## 三、Shared 模块架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Shared Module (Attempt/Shared/src)               │
└─────────────────────────────────────────────────────────────────────┘

                        ┌──────────────┐
                        │  config.py   │
                        │ (配置加载)   │
                        └──────┬───────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
    ┌────────────┐      ┌──────────────┐      ┌──────────────┐
    │   agents/  │      │data_collectors│      │   tools/     │
    │            │      │               │      │              │
    ├────────────┤      ├──────────────┤      ├──────────────┤
    │base_agent  │      │openalex_     │      │search_tool   │
    │            │      │client.py     │      │(路由器)      │
    │data_       │      │              │      │              │
    │collection_ │      │gdelt_client  │      │github_client │
    │agent.py    │      │.py           │      │              │
    │            │      │              │      │              │
    │data_       │      │              │      │              │
    │analysis_   │      │              │      │              │
    │agent.py    │      │              │      │              │
    └────────────┘      └──────────────┘      └──────────────┘
        │                      │                      │
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                        ┌──────▼──────────┐
                        │  processors/    │
                        │                 │
                        ├─────────────────┤
                        │normalize.py     │
                        │(JSONL I/O,      │
                        │ merge, pivot)   │
                        │                 │
                        │quality_checker  │
                        │.py              │
                        │(质量检查)       │
                        └─────────────────┘
```

### 3.1 Agent 框架

```
┌──────────────────────────────────────────┐
│         BaseAgent (Interface)            │
├──────────────────────────────────────────┤
│ + run() -> AgentResult                   │
└──────────────────────────────────────────┘
         △                    △
         │                    │
         │                    │
    ┌────┴──────────┐    ┌────┴──────────┐
    │DataCollection │    │DataAnalysis   │
    │Agent          │    │Agent          │
    ├───────────────┤    ├───────────────┤
    │ + run()       │    │ + run()       │
    │   ├─ 迭代主题 │    │   ├─ 加载记录 │
    │   ├─ 调用     │    │   ├─ 合并数据 │
    │   │ SearchTool│    │   ├─ 创建透视 │
    │   └─ 保存结果 │    │   └─ 质量检查 │
    └───────────────┘    └───────────────┘

AgentResult:
  ├─ ok: bool
  └─ detail: dict[str, Any]
```

### 3.2 数据采集客户端

```
┌─────────────────────────────────────────────────────────┐
│              Data Collectors                            │
└─────────────────────────────────────────────────────────┘

OpenAlex Client:
  ├─ fetch_openalex_grouped()
  │  ├─ 构建查询参数
  │  ├─ 检查缓存 (SHA256(url+params))
  │  ├─ 发送 API 请求 (group_by=publication_date)
  │  ├─ 处理 429 重试 (指数退避)
  │  └─ 保存缓存
  │
  └─ collect_openalex_topic()
     ├─ 调用 fetch_openalex_grouped()
     ├─ 本地聚合到月度窗口
     └─ 返回标准化记录列表

GDELT Client:
  ├─ fetch_gdelt_timeline()
  │  ├─ 构建时间线请求
  │  ├─ 检查缓存
  │  ├─ 发送 API 请求
  │  ├─ 处理 429 重试
  │  └─ 保存缓存
  │
  └─ collect_gdelt_topic()
     ├─ 调用 fetch_gdelt_timeline()
     ├─ 本地拆分为月度窗口
     └─ 返回标准化记录列表

GitHub Client:
  ├─ fetch_github_trending()
  │  ├─ 加载 GITHUB_TOKEN (可选)
  │  ├─ 查询新仓库 (created:>=D-7)
  │  ├─ 查询活跃仓库 (pushed:>=D-1)
  │  ├─ 应用语言/组织过滤
  │  └─ 保存快照
  │
  └─ 返回聚合信号
```

### 3.3 处理器

```
┌─────────────────────────────────────────────────────────┐
│              Processors                                 │
└─────────────────────────────────────────────────────────┘

normalize.py:
  ├─ save_records_to_jsonl()
  │  └─ list[dict] → JSONL 文件
  │
  ├─ load_jsonl()
  │  └─ JSONL 文件 → list[dict]
  │
  ├─ merge_records_by_source()
  │  └─ OpenAlex + GDELT → 合并排序列表
  │
  ├─ build_feature_matrix()
  │  └─ 按主题分组
  │
  └─ create_pivot_table()
     └─ 透视：每行一个月份，包含多源计数

quality_checker.py:
  ├─ check_data_quality()
  │  ├─ 缺失值检查
  │  ├─ 异常值检查
  │  ├─ 覆盖范围检查
  │  └─ 计算质量评分
  │
  └─ save_quality_report()
     └─ 生成 JSON 报告
```

---

## 四、实验组织结构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Experiment Organization                          │
└─────────────────────────────────────────────────────────────────────┘

Attempt/
│
├─ Shared/                    ← 共享模块（稳定接口）
│  └─ src/
│     ├─ agents/
│     ├─ data_collectors/
│     ├─ tools/
│     └─ processors/
│
├─ Baselines/                 ← 简单基线、对照实验
│  ├─ experiments/
│  │  ├─ 2026-08-14_simple_baseline/
│  │  │  ├─ README.md
│  │  │  └─ src/
│  │  │     ├─ pipeline.py (主入口)
│  │  │     ├─ baseline_model.py (MA, LR)
│  │  │     ├─ evaluator.py (MAE, MAPE, RMSE)
│  │  │     ├─ report_generator.py
│  │  │     └─ test_*.py
│  │  │
│  │  └─ technology_cultivation_forecast_00/
│  │
│  ├─ src/
│  ├─ tests/
│  └─ configs/
│
├─ Memory_Design/             ← 记忆结构实验
│  ├─ experiments/
│  ├─ src/
│  ├─ tests/
│  ├─ configs/
│  └─ docs/
│
├─ Reasoning_Architecture/    ← 推理链路实验
│  ├─ experiments/
│  ├─ src/
│  ├─ tests/
│  ├─ configs/
│  └─ docs/
│
├─ Reproduction/              ← 复现论文/项目
│  ├─ experiments/
│  ├─ src/
│  ├─ tests/
│  ├─ configs/
│  └─ docs/
│
├─ Sandbox/                   ← 短期探索
│  └─ ...
│
├─ scripts/                   ← 环境、数据检查脚本
├─ notebooks/                 ← 探索性笔记本
├─ configs/                   ← 跨实验配置
│  ├─ default.yaml
│  ├─ topics.yaml
│  └─ sources.yaml
│
└─ docs/                      ← 架构图、设计说明
```

---

## 五、基线实验流程（2026-08-14_simple_baseline）

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Baseline Experiment Pipeline                       │
└─────────────────────────────────────────────────────────────────────┘

                            START
                              │
                              ▼
                    ┌──────────────────┐
                    │ Phase 1: Collect │
                    │   Data from      │
                    │ OpenAlex, GDELT  │
                    └────────┬─────────┘
                             │
                    ┌────────▼────────┐
                    │ openalex_       │
                    │ records.jsonl   │
                    │ gdelt_records   │
                    │ .jsonl          │
                    └────────┬────────┘
                             │
                              ▼
                    ┌──────────────────┐
                    │ Phase 2: Normalize│
                    │   & Merge Data   │
                    │   Create Pivot   │
                    └────────┬─────────┘
                             │
                    ┌────────▼────────┐
                    │ pivot_table_    │
                    │ extended.jsonl  │
                    │ (每行一个月份)  │
                    └────────┬────────┘
                             │
                              ▼
                    ┌──────────────────┐
                    │ Phase 3: Baseline│
                    │  Forecasting     │
                    │ ├─ Moving Avg    │
                    │ └─ Linear Reg    │
                    └────────┬─────────┘
                             │
                    ┌────────▼────────┐
                    │ baseline_       │
                    │ results.json    │
                    │ (详细预测)      │
                    └────────┬────────┘
                             │
                              ▼
                    ┌──────────────────┐
                    │ Phase 4: Evaluate│
                    │ ├─ MAE           │
                    │ ├─ MAPE          │
                    │ └─ RMSE          │
                    └────────┬─────────┘
                             │
                    ┌────────▼────────┐
                    │ baseline_       │
                    │ evaluations     │
                    │ .json           │
                    │ summary.json    │
                    └────────┬────────┘
                             │
                              ▼
                            END
```

### 5.1 时间序列切分

```
Timeline: 2023-01 ────────────────────────────────── 2025-07

Train (70%)          │ Validation (15%) │ Test (30%)
2023-01 ─────────────┤ 2024-11 ────────┤ 2025-02 ────── 2025-07
                     │                  │
                     └──────────────────┘
                     
滚动预测：
  Month 1: 预测 Month 2 (使用 Month 1 历史)
  Month 2: 预测 Month 3 (使用 Month 1-2 历史)
  ...
  Month N: 预测 Month N+1 (使用 Month 1-N 历史)
```

---

## 六、配置驱动的参数流

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Configuration-Driven Parameters                    │
└─────────────────────────────────────────────────────────────────────┘

default.yaml
├─ project_name: predictive-agents
├─ timezone: Asia/Shanghai
├─ random_seed: 42
├─ data_root: F:\Predictive agents\Data
├─ resources_root: F:\Predictive agents\Resources
└─ default_data_split:
   ├─ train_ratio: 0.7
   ├─ validation_ratio: 0.15
   └─ test_ratio: 0.15
        │
        ▼
   PipelineConfig (dataclass)
   ├─ 路径属性 (自动生成)
   │  ├─ raw_api_path
   │  ├─ interim_path
   │  ├─ processed_path
   │  └─ reports_path
   │
   └─ 主题列表
      └─ topics: list[TopicConfig]

topics.yaml
├─ topics:
│  ├─ llm
│  │  ├─ topic_id: llm
│  │  ├─ topic_label: Large Language Models
│  │  ├─ openalex_query: large language model
│  │  └─ gdelt_query: "large language model"
│  │
│  ├─ ai_agent
│  ├─ robotics
│  ├─ quantum_comp
│  └─ edge_comp
        │
        ▼
   TopicConfig (dataclass)
   ├─ topic_id
   ├─ topic_label
   ├─ openalex_query
   └─ gdelt_query

sources.yaml
├─ sources:
│  ├─ openalex:
│  │  └─ enabled: true
│  │
│  ├─ gdelt:
│  │  └─ enabled: true
│  │
│  └─ github:
│     ├─ enabled: true
│     ├─ k_new: 100
│     ├─ k_active: 50
│     ├─ delta_7d_threshold: 100
│     ├─ use_llm_summarize: false
│     ├─ language_whitelist: []
│     └─ org_whitelist: []
        │
        ▼
   SearchTool 路由参数
   ├─ 启用/禁用数据源
   ├─ GitHub 搜索参数
   └─ 过滤条件
```

---

## 七、API 缓存机制

```
┌─────────────────────────────────────────────────────────────────────┐
│                      API Caching Strategy                           │
└─────────────────────────────────────────────────────────────────────┘

API 请求
  │
  ├─ 构建 URL + 参数
  │
  ├─ 计算缓存键
  │  └─ SHA256(json.dumps({"url": url, "params": params}))[:16]
  │
  ├─ 检查缓存文件
  │  └─ cache_dir / f"{key}.json"
  │
  ├─ 缓存命中？
  │  ├─ YES → 返回缓存数据
  │  │
  │  └─ NO → 发送 HTTP 请求
  │     │
  │     ├─ 速率限制 (sleep)
  │     │
  │     ├─ 429 Too Many Requests?
  │     │  ├─ YES → 指数退避重试
  │     │  └─ NO → 继续
  │     │
  │     ├─ 保存响应到缓存
  │     │
  │     └─ 返回数据
  │
  └─ 返回标准化记录
```

---

## 八、数据质量检查流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Data Quality Check Flow                          │
└─────────────────────────────────────────────────────────────────────┘

pivot_table_extended.jsonl
        │
        ▼
┌──────────────────────────────┐
│ check_data_quality()         │
├──────────────────────────────┤
│ 1. 缺失值检查                │
│    ├─ 每个主题的记录数       │
│    ├─ 每个数据源的覆盖率     │
│    └─ 时间窗口的完整性       │
│                              │
│ 2. 异常值检查                │
│    ├─ 计数为 0 的比例        │
│    ├─ 极端值 (IQR 方法)      │
│    └─ 时间序列平滑性         │
│                              │
│ 3. 覆盖范围检查              │
│    ├─ 主题覆盖率             │
│    ├─ 时间覆盖率             │
│    └─ 数据源覆盖率           │
│                              │
│ 4. 计算质量评分              │
│    ├─ 0-100 分               │
│    └─ 加权平均               │
└──────────────────────────────┘
        │
        ▼
quality_report.json
├─ overall_score: float
├─ by_topic: dict
├─ by_source: dict
├─ missing_values: dict
├─ anomalies: dict
└─ coverage: dict
```

---

## 九、模块依赖关系

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Module Dependencies                              │
└─────────────────────────────────────────────────────────────────────┘

Baselines/experiments/2026-08-14_simple_baseline/src/pipeline.py
  │
  ├─ imports from Shared/src/
  │  ├─ config.py
  │  │  └─ load_pipeline_config(), generate_monthly_windows()
  │  │
  │  ├─ data_collectors/
  │  │  ├─ openalex_client.py
  │  │  │  └─ collect_openalex_topic()
  │  │  │
  │  │  └─ gdelt_client.py
  │  │     └─ collect_gdelt_topic()
  │  │
  │  └─ processors/
  │     ├─ normalize.py
  │     │  ├─ merge_records_by_source()
  │     │  ├─ create_pivot_table()
  │     │  ├─ save_records_to_jsonl()
  │     │  └─ load_jsonl()
  │     │
  │     └─ quality_checker.py
  │        └─ check_data_quality()
  │
  └─ imports from local src/
     ├─ baseline_model.py
     │  ├─ moving_average_forecast()
     │  ├─ linear_regression_forecast()
     │  └─ forecast_topic()
     │
     ├─ evaluator.py
     │  ├─ evaluate_forecast()
     │  └─ summarize_results()
     │
     └─ report_generator.py
        └─ generate_report()

External Dependencies:
  ├─ numpy (数值计算)
  ├─ pandas (数据处理)
  ├─ pydantic (数据验证)
  ├─ pyyaml (配置解析)
  ├─ requests (HTTP 请求)
  ├─ python-dotenv (环境变量)
  └─ scikit-learn (机器学习)
```

---

## 十、错误处理与恢复

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Error Handling & Recovery                          │
└─────────────────────────────────────────────────────────────────────┘

API 请求失败
  │
  ├─ 429 Too Many Requests
  │  └─ 指数退避重试 (最多 5 次)
  │     └─ 等待时间: 30s × (attempt + 1)
  │
  ├─ 网络超时
  │  └─ 检查缓存 (如果有)
  │     ├─ YES → 使用缓存数据
  │     └─ NO → 记录错误，继续下一个主题
  │
  ├─ 无效响应格式
  │  └─ 记录错误，继续下一个主题
  │
  └─ 其他错误
     └─ 记录到 collection_report.json
        └─ 继续处理其他主题

数据处理失败
  │
  ├─ JSONL 文件不存在
  │  └─ 返回空列表，继续
  │
  ├─ JSON 解析错误
  │  └─ 跳过该行，继续
  │
  └─ 数据类型不匹配
     └─ 尝试类型转换，失败则跳过

Agent 执行失败
  │
  └─ 返回 AgentResult(ok=False, detail={"error": str(e)})
     └─ 上层调用者检查 ok 标志，决定是否继续
```

---

## 十一、扩展点

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Extension Points                               │
└─────────────────────────────────────────────────────────────────────┘

1. 新增数据源
   └─ 实现 data_collectors/new_source_client.py
      ├─ fetch_new_source_grouped()
      └─ collect_new_source_topic()
      
      在 tools/search_tool.py 中添加路由
      └─ if source == "new_source": ...

2. 新增预测模型
   └─ Baselines/experiments/YYYY-MM-DD_new_model/src/
      ├─ new_model.py (模型实现)
      ├─ evaluator.py (评估逻辑)
      └─ pipeline.py (主入口)

3. 新增 Agent
   └─ Shared/src/agents/new_agent.py
      ├─ 继承 BaseAgent
      └─ 实现 run() 方法

4. 新增处理器
   └─ Shared/src/processors/new_processor.py
      └─ 在 DataAnalysisAgent 中调用

5. 新增主题
   └─ 编辑 configs/topics.yaml
      └─ 添加新的 TopicConfig 条目

6. 新增数据源参数
   └─ 编辑 configs/sources.yaml
      └─ 在 SearchTool 中使用
```

---

## 十二、关键路径

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Critical Paths                                 │
└─────────────────────────────────────────────────────────────────────┘

最快路径（仅使用缓存）：
  pipeline.py
    └─ run_collection() (使用缓存的 API 响应)
       └─ 1-2 秒

完整路径（新数据采集）：
  pipeline.py
    ├─ run_collection() (新 API 请求)
    │  ├─ OpenAlex: 3 秒 × 主题数
    │  ├─ GDELT: 10 秒 × 主题数
    │  └─ GitHub: 0.4-1.5 秒 × 主题数
    │
    ├─ run_normalization()
    │  └─ 1-2 秒
    │
    ├─ run_forecasting()
    │  └─ 1-2 秒
    │
    └─ run_evaluation()
       └─ 1-2 秒

总耗时估计：
  ├─ 缓存命中：< 5 秒
  ├─ 新采集 (5 主题)：
  │  ├─ OpenAlex: 15 秒
  │  ├─ GDELT: 50 秒
  │  ├─ GitHub: 5-10 秒
  │  └─ 总计：70-75 秒
  │
  └─ 首次运行：1-2 分钟
```

---

**架构图生成时间**：2026-08-17  
**项目根目录**：`F:\Predictive agents`
