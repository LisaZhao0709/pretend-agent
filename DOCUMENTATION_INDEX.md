# 预测智能体项目 - 文档索引与快速参考指南

本项目为跨领域技术趋势预测智能体（Predictive Agents）的长期科研项目。本文档整合了**系统文档全局索引**与日常研发所需的**速查参考卡（Quick Reference）**。

---

## 📚 一、核心文档导航地图

```
F:\Predictive agents/
│
├── DOCUMENTATION_INDEX.md (本文件 - 全局导航与研发速查)
│
├── TECHNICAL_FRAMEWORK_SUMMARY.md ⭐⭐⭐
│   └── 权威技术框架总结（三层架构、数据流转、特征工程、无前瞻偏差清洗、评价体系与研报智能体）
│
├── ARCHITECTURE_DIAGRAM.md ⭐⭐⭐
│   └── 系统可视化架构图解（ASCII 管道流、时序处理、DeepSeek 直连拓扑、参数流转）
│
├── AGENTS.md ⭐⭐
│   └── 研发行为规范与工作协议（命名规范、版本控制、数据完整性、用户审核停机规则）
│
├── README.md ⭐
│   └── 项目快速启动指引
│
└── 模块专项目录
    ├── Attempt/README.md              # 实验组织规范与版本机制
    ├── Attempt/Shared/README.md       # 共享基础库说明
    └── Data/README.md                 # 数据分层与元数据规范
```

---

## ⚡ 二、快速运行与日常开发速查（Quick Reference）

### 2.1 项目基本信息
| 项 | 配置/值 |
| :--- | :--- |
| **项目名称** | Predictive Agents |
| **项目根目录** | `F:\Predictive agents` |
| **主实验目录** | `Attempt/Baselines/experiments/technology_cultivation_forecast_01` |
| **推荐 Python** | `Python 3.11.9` (`C:\Users\Xiaol\AppData\Local\Programs\Python\Python311\python.exe`) |
| **核心外部接口** | DeepSeek Chat API (`https://api.deepseek.com/chat/completions`)、CrossRef、GDELT、OpenAlex |
| **环境变量文件** | `Attempt/.env`（包含 `DEEPSEEK_API_KEY`） |

---

### 2.2 四种一键运行流水线方式

1. **双击运行（最便捷）**：
   直接在文件管理器中双击根目录下的 [`run.bat`](file:///F:/Predictive%20agents/run.bat)，运行结束自动暂停展示结果报告路径。
2. **VS Code / IDE 快捷键 `F5`**：
   在编辑器任意代码页按 **`F5`**（或 `Ctrl + F5`），立即启动预测流水线。
3. **VS Code 任务快捷键 `Ctrl + Shift + B`**：
   按快捷键直接触发后台/控制台任务。
4. **终端命令行**：
   ```powershell
   cd "F:\Predictive agents\Attempt"
   python -u run_pipeline.py
   ```

---

### 2.3 常用开发与测试命令

```powershell
# 1. 运行最小化单元测试
cd "F:\Predictive agents\Attempt"
pytest tests/ -v

# 2. 仅测试数据清洗与前瞻偏差校验
pytest tests/test_cleaner.py -v

# 3. 运行代码规范与格式检查
ruff check .
ruff format .

# 4. 查看当前 Python 环境安装包
& "C:\Users\Xiaol\AppData\Local\Programs\Python\Python311\python.exe" -m pip list
```

---

### 2.4 核心代码常用片段

#### 加载全局配置
```python
from config import load_pipeline_config

cfg = load_pipeline_config()
print("数据目录:", cfg.data_root)
print("透视宽表目录:", cfg.processed_path)
print("报告生成目录:", cfg.reports_path)
```

#### 调用直连 DeepSeek 研报智能体
```python
from agents.reporting_agent import ReportingAgent

agent = ReportingAgent(
    backtest_path=cfg.reports_path / "backtest_latest.json",
    ranking_path=cfg.reports_path / "forecast_ranking_latest.json",
    output_path=cfg.reports_path / "final_report.md"
)
result = agent.run()
print("研报生成成功:", result.ok)
```

---

### 2.5 配置文件速查

所有频繁变动的实验参数集中在 `Attempt/configs/` 中：

1. **`default.yaml`**：
   ```yaml
   project_name: predictive-agents
   timezone: Asia/Shanghai
   random_seed: 42
   data_root: F:\Predictive agents\Data
   ```
2. **`topics.yaml`**：
   定义监测的技术领域（如 `embodied_ai`, `neuromorphic_computing`, `generative_ai`, `quantum_computing` 等），包含各数据源对应的中英文查询词。
3. **`sources.yaml`**：
   控制数据源开关（`enabled: true/false`）、超时时间、请求间隔限制、GitHub 过滤规则。

---

## 🔧 三、常见问题与错误排查指南（Troubleshooting）

| 常见现象 / 错误信息 | 产生原因 | 解决办法 |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'yaml'` 或其他依赖缺失 | VS Code 自动切到了 `uv` 的全新 Python 3.14，或未选择已配置好的 Python 3.11 解释器。 | 按 `Ctrl+Shift+P` -> `Python: Select Interpreter`，选择 `Python 3.11.9 (C:\Users\Xiaol\AppData\Local\Programs\Python\Python311\python.exe)`。项目已在 `.vscode/settings.json` 中配置默认路径。 |
| `KeyError: 'DEEPSEEK_API_KEY'` | `Attempt/.env` 文件缺失或未配置 API Key。 | 在 `Attempt/.env` 中写入 `DEEPSEEK_API_KEY=sk-xxxx`，参考 `Attempt/.env.example`。 |
| GDELT 或 arXiv API 超时 / 429 报错 | 国内网络直连 GDELT 或 arXiv 偶发 SSL 握手超时或频控拦截。 | 保持 `sources.yaml` 中使用本地中间态缓存；流水线已具备自动使用 `Data/Interim/...` 缓存机制。 |
| 透视宽表数据全被过滤为空 | 清洗器误将包含未启用数据源的全零列当成异常行剔除。 | `cleaner.py` 已更新为动态只评估活跃列（`sum() > 0`），不会因部分数据源未采集而丢失记录。 |

---

## 🎯 四、任务场景快速导览

- **想了解系统各模块职责与数学模型公式？**
  👉 查阅 [TECHNICAL_FRAMEWORK_SUMMARY.md](file:///F:/Predictive%20agents/TECHNICAL_FRAMEWORK_SUMMARY.md)
- **想查看数据流、因果平滑与网络缓存时序图？**
  👉 查阅 [ARCHITECTURE_DIAGRAM.md](file:///F:/Predictive%20agents/ARCHITECTURE_DIAGRAM.md)
- **想修改代码前确认规则与停机规范？**
  👉 查阅 [AGENTS.md](file:///F:/Predictive%20agents/AGENTS.md)
- **想快速运行一次完整预测并查看新产出的研报？**
  👉 双击 [run.bat](file:///F:/Predictive%20agents/run.bat)，完成后查看 [`Data/Reports/technology_cultivation_01/final_report.md`](file:///F:/Predictive%20agents/Data/Reports/technology_cultivation_01/final_report.md)
