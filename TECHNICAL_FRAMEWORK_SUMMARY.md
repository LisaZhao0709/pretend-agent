# 预测智能体项目 - 技术框架综合总结

**项目根目录**：`F:\Predictive agents`  
**项目定位**：长期本科科研项目（自主研发跨领域技术趋势预测智能体）  
**更新时间**：2026-09  
**当前演进版本**：`technology_cultivation_forecast_01`

---

## 一、系统整体架构

项目严格遵循三层物理隔离架构，保证数据、资源、代码与配置的清晰分离与版本可复现性：

```
F:\Predictive agents/
├── Resources/              # 外部文献、技术调研、项目综述、历史阅读笔记
├── Data/                  # 数据资产管理（只追加不覆盖，严格分层）
│   ├── Raw/               # 原始 API 响应及抓取记录（不可变）
│   ├── Interim/           # 清洗与格式对齐的中间态数据（JSONL）
│   ├── Processed/         # 标准化后的透视宽表与特征矩阵
│   ├── Reports/           # 自动生成的质量报告、回测指标与大模型综合分析报告
│   ├── Cache/             # API 响应持久化缓存（SQLite api_cache_v2.db + JSON）
│   ├── Metadata/          # 数据来源、采集参数、授权及血缘说明
│   └── Schemas/           # 字段定义与数据契约校验规范
└── Attempt/               # 实验代码、共享核心库、环境及配置文件
    ├── Shared/            # 核心共享基础库（跨实验复用）
    ├── Baselines/         # 基线模型与对照实验（如 technology_cultivation_forecast_01）
    ├── Memory_Design/     # 智能体长短期记忆与时序上下文管理实验
    ├── Reasoning_Architecture/ # 推理决策链路与 Agent 拓扑架构实验
    ├── Reproduction/      # 顶会论文与开源方案复现
    ├── Sandbox/           # 原型验证与探索性脚本
    ├── configs/           # 集中式配置文件（default.yaml, topics.yaml, sources.yaml）
    ├── run_pipeline.py    # 全流程一键端到端执行脚本
    └── .env               # 本地私密环境变量（API Keys，绝不入库）
```

---

## 二、端到端数据与预测流转（Data & Forecast Pipeline）

整个流水线从外部学术/技术多源数据采集，到无未来信息泄露的特征预处理，再到多周期排序回测，最终由 DeepSeek 智能体产出综合决策研报，全链路完全自动化：

```
[configs/topics.yaml & sources.yaml]
                │
                ▼
1. 多源数据采集 (DataCollectionAgent & PoliteApiClient)
   - CrossRef / OpenAlex / GDELT / GitHub / arXiv
   - 本地 SQLite 缓存优先 + 速率限制 + 指数退避
                │
                ▼ (Data/Interim/*.jsonl)
2. 无前瞻偏差的数据清洗与对齐 (DataAnalysisAgent & Processors)
   - cleaner.py: 单向因果平滑 (无 center=True, 无 bfill)
   - detector.py: 滚动历史 6 个月滑动窗口异常值检测
   - normalize.py: 截面 Z-Score 标准化 (Group by window_start)
                │
                ▼ (Data/Processed/pivot_table_extended.jsonl)
3. 相对注意力份额与动量特征工程 (scoring.py)
   - 相对注意力份额: Share_t = (count_t + 1) / (Total_t + 6)
   - 趋势动量与 MACD: (Share_MACD / Share_EMA)
                │
                ▼
4. 多周期前向排序回测 (Walk-Forward Backtesting)
   - 1 个月 Horizon: Top-1 相对提升率、Spearman 秩相关系数、NDCG@3、NDCG@5
   - 3 个月 Horizon: 中长期趋势捕获能力评估
                │
                ▼ (Data/Reports/.../backtest_latest.json & forecast_ranking_latest.json)
5. 研报智能体直接集成 (ReportingAgent - DeepSeek Direct HTTP)
   - 无需 openai 外部库，纯原生 HTTP 访问 api.deepseek.com
   - 自动整合回测指标、Top-3 爆发技术、风险预警与科研建议
                │
                ▼
6. 最终交付物: Data/Reports/technology_cultivation_01/final_report.md
```

---

## 三、核心模块与技术实现

### 3.1 共享核心层 (`Attempt/Shared/src/`)

| 模块类别 | 文件名 | 核心职责与设计要点 |
| :--- | :--- | :--- |
| **网络与缓存** | `http_client.py` | `PoliteApiClient`：内置令牌桶速率限制、指数退避重试；采用 SQLite `api_cache_v2.db` 持久化，兼容旧版 `_00` 的哈希 JSON 缓存兜底。 |
| **配置管理** | `config.py` | 统一加载 `default.yaml`、`topics.yaml`、`sources.yaml`，动态派生各层数据目录，杜绝业务代码硬编码路径。 |
| **数据采集器** | `data_collectors/` | `CrossRefClient`、`OpenAlexClient`、`GDELTClient`、`ArxivClient`、`GitHubClient`。标准化输出为统一的月度时序点。 |
| **路由工具** | `tools/search_tool.py` | `SearchTool`：根据数据源名称分发采集任务，处理鉴权令牌（如 `GITHUB_TOKEN`）。 |
| **数据清洗器** | `processors/cleaner.py` | **彻底消除前瞻偏差（Look-ahead Bias）**：严禁 `center=True` 与 `bfill()`，仅使用纯历史单向窗口；动态识别全零非活跃列，避免误删行。 |
| **异常检测器** | `processors/detector.py` | 滚动历史 6 个月（`window=6`）的动态 Z-Score 与 IQR 检验，杜绝全生命周期全局统计量泄露。 |
| **截面标准化** | `processors/normalize.py` | 透视表构建与基于各时间切片（`window_start`）的截面 Z-Score 标准化，保证不同技术在同一时间维度的可比性。 |
| **质量检查器** | `processors/quality_checker.py` | 评估缺失率、覆盖度、异常值占比，输出规范化的 `quality_report.json`。 |
| **智能体框架** | `agents/base_agent.py` | 定义 `BaseAgent` 抽象基类与 `AgentResult` 统一返回契约。 |
| **采集智能体** | `agents/data_collection_agent.py` | 编排主题与数据源的抓取循环，统计成功率与耗时。 |
| **分析智能体** | `agents/data_analysis_agent.py` | 负责中间态数据解析、透视宽表拼接与数据质量报告生成。 |
| **研报智能体** | `agents/reporting_agent.py` | **DeepSeek 官方 API 直连**：纯原生 HTTP POST 调用 `https://api.deepseek.com/chat/completions`，无需 `openai` 客户端库及梯子依赖；结合真实回测与预测指标输出严谨科研报告。 |

---

### 3.2 预测算法与评价体系 (`Attempt/Baselines/experiments/technology_cultivation_forecast_01/`)

本版本针对早期 `_00` 版本的绝对技术热度与简单短期预测进行了全面升级：

#### 1. 相对注意力份额（Relative Attention Share）
针对传统直接使用“论文数/热度值”导致头部成熟技术（如经典深度学习）永远霸榜的问题，引入相对注意力份额指标，并加入 Laplace 平滑防止分母为零：
$$Share_{i,t} = \frac{\text{Count}_{i,t} + 1}{\sum_{j} \text{Count}_{j,t} + N}$$
其中 $N$ 为当前跟踪的技术主题总数（如 6 个）。

#### 2. 相对动量增长（Relative Momentum Growth）
在相对份额时序上计算快速指数移动平均（EMA）与平滑异同移动平均（MACD），构建无量纲的技术关注度增速：
$$Growth_{i,t} = \frac{MACD_{Share, i, t}}{EMA_{Share, i, t}}$$

#### 3. 多预测周期评价（Multi-Horizon Backtesting）
流水线支持评估不同时间跨度的前向预测效果：
- **1 个月短期动量（1-Month Horizon）**：捕获突发性技术爆发点。
- **3 个月季度趋势（3-Month Horizon）**：过滤单月噪声，评估技术中期成长稳定性。

#### 4. 排序质量评估指标（Ranking Metrics）
- **Top-1 Lift（首位相对提升率）**：评估模型推荐的 Top-1 技术在未来实际增长中相比技术池平均水平的超额倍数。
- **Spearman $\rho$（秩相关系数）**：衡量全部技术预测排序与未来实际增长排序的单调相关性（范围 $[-1, 1]$）。
- **NDCG@K（归一化折损累计增益）**：针对技术雷达场景，核心关注 Top-3 与 Top-5 的排序命中精度：
  $$DCG@K = \sum_{i=1}^K \frac{rel_i}{\log_2(i + 1)}, \quad NDCG@K = \frac{DCG@K}{IDCG@K}$$

---

## 四、配置系统规范

所有动态调优参数均集中在 `Attempt/configs/` 下，严禁硬编码在业务逻辑中：

1. **`default.yaml`**：
   - 全局时区（`Asia/Shanghai`）、随机数种子（`42`）、数据根目录映射、训练/验证/测试比例。
2. **`topics.yaml`**：
   - 技术主题元数据：ID、中英文标签、多源检索查询词（支持跨领域技术如具身智能、神经拟态、生成式 AI、量子计算等）。
3. **`sources.yaml`**：
   - 各数据源开关（`enabled: true/false`）、超时时间、请求间隔限制、GitHub 筛选参数（`k_new`, `k_active`）等。

---

## 五、环境与快速运行方式

### 5.1 运行环境
- **Python 版本**：`Python 3.11.9`（推荐，系统路径：`C:\Users\Xiaol\AppData\Local\Programs\Python\Python311\python.exe`）
- **核心依赖**：`pandas`, `numpy`, `pyyaml`, `aiohttp`, `requests`, `scikit-learn`, `scipy`, `python-dotenv`
- **环境变量**：`Attempt/.env` 中配置 `DEEPSEEK_API_KEY=sk-...`

### 5.2 三种一键启动方式
1. **双击启动**：双击项目根目录下的 [`run.bat`](file:///F:/Predictive%20agents/run.bat)，自动锁定环境并在完成后暂停展示报告路径。
2. **编辑器快捷键 `F5`**：在 VS Code / Antigravity IDE 中随时按下 `F5`（通过 `.vscode/launch.json` 配置）。
3. **任务快捷键 `Ctrl + Shift + B`**：一键运行构建任务并在终端输出日志。
4. **CLI 命令行**：
   ```powershell
   cd "F:\Predictive agents\Attempt"
   python -u run_pipeline.py
   ```

---

## 六、交付物与产出文件清单

每次运行流水线后，会自动生成并刷新以下结构化结果：

| 文件路径 | 格式 | 说明 |
| :--- | :--- | :--- |
| `Data/Processed/technology_cultivation_01/pivot_table_extended.jsonl` | JSONL | 经过因果清洗、截面标准化的多源时间序列透视宽表 |
| `Data/Reports/technology_cultivation_01/backtest_latest.json` | JSON | 包含 28 个历史回测窗口在 1M 与 3M Horizon 下的 Top-1 Lift、Spearman $\rho$、NDCG@3/5 详尽指标 |
| `Data/Reports/technology_cultivation_01/forecast_ranking_latest.json` | JSON | 基于最新窗口生成的下一周期各技术推荐关注度与排序得分 |
| `Data/Reports/technology_cultivation_01/final_report.md` | Markdown | 由 DeepSeek 直连调用的研报智能体生成的完整学术级预测与分析决策报告 |
