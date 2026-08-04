# Predictive Agents

这是一个用于研究、实现和回顾预测类 Agent 的长期项目空间。项目根目录位于 `F:\Predictive agents`。

## 目录说明

- `Resources/`：外部资料和自己的历史整理。放论文、说明文档、项目介绍、技术报告、阅读笔记及历史进展。
- `Data/`：预测类 Agent 使用的数据。按来源、处理阶段和用途保存爬虫数据、论文网站 API 数据、下载文件、元数据和数据报告。
- `Attempt/`：所有代码、环境配置和实验记录。每次尝试都应放进对应的分类目录，并留下可复现的说明。

## 推荐工作流

1. 把外部资料放到 `Resources/`，文件名使用英文；中文解释写在同目录的 `README.md` 或记录文档里。
2. 把原始数据放到 `Data/Raw/`，不要直接覆盖原始文件。
3. 数据清洗和转换依次使用 `Data/Interim/`、`Data/Processed/`，并在 `Data/Metadata/` 记录来源、时间、字段和处理步骤。
4. 新实验先复制 `Attempt/_template/` 的结构，再放进 `Memory_Design/`、`Reasoning_Architecture/`、`Reproduction/`、`Baselines/` 或 `Sandbox/`。
5. 每次尝试都填写 `README.md`，记录目标、假设、输入、运行命令、结果、问题和下一步。

## 命名约定

- 文件夹、代码文件、配置项和数据集文件名使用英文和 `snake_case` 或 `PascalCase`。
- 日期统一使用 `YYYY-MM-DD`，例如 `2026-08-04`。
- 不删除原始数据；如果需要更新，创建带版本或日期的新文件。
- 避免把密钥、密码、个人访问令牌和未脱敏数据提交到 Git。

## 快速入口

- 资料规范：`Resources/README.md`
- 数据规范：`Data/README.md`
- 实验规范：`Attempt/README.md`
- 实验模板：`Attempt/_template/README.md`
