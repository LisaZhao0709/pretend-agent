# Attempt

这里保存 Predictive Agents 的所有代码尝试、实验配置、环境定义、运行记录和回顾文档。任何尝试都应归入明确的类别，不要把长期代码和一次性试验混在根目录。

## 分类

- `Memory_Design/`：记忆结构、记忆写入/检索/压缩、长期记忆和上下文管理。
- `Reasoning_Architecture/`：推理链路、规划、工具调用、预测流程和架构组合。
- `Reproduction/`：复现论文、开源项目或他人已完成的实验。
- `Baselines/`：简单基线、传统方法、无 Agent 方法和对照实验。
- `Sandbox/`：尚未归类、短期验证和风险较低的探索。
- `Shared/`：多个分类共用的工具、评测、数据加载器、Agent 和通用模块。
  - `src/tools/`：数据采集工具（OpenAlex、GDELT、GitHub 等）和统一搜索接口。
  - `src/agents/`：多 Agent 架构（DataCollectionAgent、DataAnalysisAgent、PredictionAgent、ReportAgent）。
  - `src/processors/`：数据规范化、质量检查和特征提取。
  - `src/data_collectors/`：API 客户端（openalex_client、gdelt_client）。
- `scripts/`：环境、数据检查和重复运行脚本。
- `notebooks/`：探索性 notebook；稳定逻辑应迁移到分类目录的 `src/`。
- `configs/`：跨实验的公共配置。
- `docs/`：跨实验设计说明、架构图和阶段回顾。

## 单次尝试的最低结构

每个尝试建议建立在对应分类下的 `experiments/YYYY-MM-DD_short_name/`：

```text
README.md       # 中文实验说明和结果回顾
src/            # 可复用代码
tests/          # 最小验证和回归测试
configs/        # 参数、数据版本、模型和运行配置
docs/           # 额外设计说明
```

## README 必须回答

1. 这次尝试想验证什么？
2. 使用了哪个数据版本和哪些外部资料？
3. 如何安装和运行？
4. 结果是什么，指标如何解释？
5. 哪些假设失败了，下一步是什么？

## 环境

环境定义在本目录根部：`pyproject.toml`、`requirements.txt`、`environment.yml` 和 `.env.example`。虚拟环境目录为 `Attempt/.venv/`，已加入 Git 忽略规则。
