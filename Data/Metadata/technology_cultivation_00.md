# Dataset Card: Technology Cultivation 00

## 中文说明

这是 `technology_cultivation_forecast_00` 使用的公开活动信号数据说明。它把学术研究活动和公司公开研发/产业布局活动作为两个独立信号源，用于预测技术主题的短期联合培养势能。

## Provenance

- Academic Source: OpenAlex Works API
- Corporate Source: GDELT DOC 2.0 API, `timelinevolraw`
- Collection Method: public API
- Source URLs: `https://api.openalex.org/works`, `https://api.gdeltproject.org/api/v2/doc/doc`
- Collection Time: recorded in each raw cache response and activity record
- License or Usage Restriction: follow the current terms and rate limits of each provider
- Contact or Maintainer: project owner

## Schema

- Raw cache: JSON response plus request URL, selected headers, and fetch time
- Processed records: JSONL
- Key fields: `source`, `topic_id`, `topic_label`, `window_start`, `window_end`, `activity_count`, `collected_at`
- Entity identifier: `topic_id`
- Time field: `window_start`, `window_end`
- Target field: future-window activity used by backtest

## Processing History

1. Query one configured topic for one historical time window.
2. Cache the raw JSON response using a hash of URL, parameters, and version key.
3. OpenAlex uses the returned `meta.count`.
4. GDELT sums raw timeline values, accepting either `timeline` or `data` response fields.
5. Store normalized activity records in `Data/Interim/technology_cultivation_00/`.

## Quality Notes

- OpenAlex publication counts depend on indexing and publication-date assignment.
- GDELT measures monitored news coverage, not all corporate activity.
- Topic queries can overlap, especially for LLMs, AI agents, and robotics.
- No causal interpretation is made from the activity counts.
- Raw API responses are intentionally not committed to Git by default.
