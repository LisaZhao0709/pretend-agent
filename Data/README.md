# Data

这里保存预测类 Agent 使用的所有数据，包括爬虫数据、论文网站 API 数据、下载文件、清洗结果、数据字典和质量报告。

## 数据流转

```text
Raw -> Interim -> Processed
  \-> Metadata / Schemas / Reports
```

- `Raw/`：刚从爬虫、API 或下载渠道获取的数据。原则上只追加，不覆盖。
- `External/`：外部数据集或论文配套数据，按来源继续分类。
- `Interim/`：正在清洗、拆分、标准化中的中间数据。
- `Processed/`：可以被实验直接消费的版本化数据。
- `Metadata/`：来源、抓取时间、许可、字段说明、哈希和处理历史。
- `Schemas/`：JSON Schema、字段定义、数据字典和校验规则。
- `Reports/`：数据质量、覆盖范围、去重和分布检查报告。
- `Cache/`：临时缓存，不提交 Git。

## 数据命名

使用英文、可排序、能表达来源和日期的名字，例如：

`source_topic_2026-08-04_v001.jsonl`

每个数据集都应有对应的数据说明文件，优先使用 `Metadata/dataset_card_template.md`。说明文档可以用中文。

## 最低记录要求

来源、采集方式、采集时间、原始 URL 或 API、许可/使用限制、字段定义、去重规则、清洗步骤、文件哈希和对应实验。

## 云端备份（可选）

`Data/Processed` 支持同步到华为云 OBS 对象存储，作为本地文件之外的云端备份，本地文件始终是数据的唯一权威来源，云端只是备份/共享入口。

- 配置文件：`Attempt/configs/cloud_storage.yaml`（默认 `enabled: false`，需要手动开启）
- 凭证：在 `.env` 中设置 `HUAWEICLOUD_AK` / `HUAWEICLOUD_SK`（参考 `Attempt/.env.example`），凭证不写入任何配置文件或 Git
- 代码入口：`Attempt/Shared/src/cloud_storage.py` 提供 `upload_file` / `download_file` / `sync_processed_data`
- 选型理由和成本估算见项目历史进展记录（华为云 OBS 标准存储约 ¥0.099/GB/月，当前数据量下月成本可忽略；数据量增长到 GB 级后再评估升级到华为云 RDS for PostgreSQL）
