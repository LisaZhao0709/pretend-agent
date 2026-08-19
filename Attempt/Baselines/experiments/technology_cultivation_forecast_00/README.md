# Technology Cultivation Forecast 00

## 中文说明

这是 Predictive Agents 的第一个可运行预测实验。目标不是直接预测某项技术最终是否商业成功，而是根据公开可观测信号，预测未来 30 天哪些技术主题会继续获得学术研究和公司研发/产业布局活动。

本版本是透明基线，不使用 LLM 直接决定分数，也不使用多 Agent。它用于先验证“数据获取—时间序列—趋势评分—回测—报告”链路。

## Objective

- Category: Baselines
- Version: 00
- Status: running
- Forecast horizon: 30 days
- Academic signal: OpenAlex scholarly work counts
- Corporate signal: GDELT public news coverage counts
- Initial topics: AI agents, large language models, embodied intelligence, robotics, quantum computing, metaverse

## Research Question

基于公开学术研究活动和企业技术发展活动，哪些技术主题的联合培养势能将在未来 30 天增强？

## Operational Definition

“公司重点培养”在本实验中仅指公开可观测的研发与产业布局活动，包括产品发布、技术合作、投资、招聘、专利或公司公告等公开信号。GDELT 新闻活动是第一版的代理指标，不能等价于公司的内部战略或真实收入增长。

## Design

```text
OpenAlex API ─┐
              ├─ period activity ─ trend features ─ rankings ─ report
GDELT API ────┘
```

For each topic and signal, the scorer uses:

1. recent level: activity in the latest window;
2. growth: recent window versus the previous window;
3. acceleration: change in growth across two adjacent windows;
4. persistence: fraction of recent observations with activity.

The academic and corporate scores are normalized within each snapshot. The joint score is the configurable weighted geometric mean, which penalizes topics that are strong on only one side.

## Compliance and Rate Limiting

- Only public APIs are used; this version does not crawl HTML pages.
- A descriptive `User-Agent` is sent on every request.
- Requests are spaced by `min_interval_seconds`.
- HTTP 429 honors `Retry-After` when present and otherwise uses exponential backoff with jitter.
- Raw responses and request metadata are cached locally to prevent duplicate requests.
- API keys are read only from environment variables and are never written to source files.

## Setup

From the repository root, use the existing project environment or create a local one:

```powershell
Set-Location 'F:\Predictive agents\Attempt'
uv venv .venv --python 3.11
uv pip install -e .
```

If an OpenAlex API key is available, set it only in the local environment. A real contact email is recommended for responsible API identification:

```powershell
$env:OPENALEX_API_KEY = 'your-local-key'
$env:PROJECT_CONTACT_EMAIL = 'your-real-email@example.com'
```

## Run

From the experiment directory:

```powershell
Set-Location 'F:\Predictive agents\Attempt\Baselines\experiments\technology_cultivation_forecast_00'
python -m src.cli --config configs/forecast_00.yaml --mode collect
python -m src.cli --config configs/forecast_00.yaml --mode score --as-of 2026-08-13
python -m src.cli --config configs/forecast_00.yaml --mode backtest --as-of 2026-08-13
```

The exact command, collection time, API responses, configuration, and output paths must be recorded in the version notes.

## Evaluation

The first evaluation is a rolling time split. At each historical cutoff, the scorer ranks topics using only data before the cutoff and checks whether the top-ranked topics show higher activity in the following 30 days. This is a directional ranking experiment, not a causal claim.

## Limitations

- OpenAlex publication dates and GDELT coverage are imperfect proxies for research and corporate development.
- News volume is affected by media attention, duplication, language coverage, and major events.
- A 30-day horizon is short and noisy.
- The initial topic vocabulary is manually seeded; automatic topic discovery is deferred to a later version.
- The version does not yet use company-level entity resolution or direct job, patent, funding, or product datasets.

## Next Steps

- Complete a first controlled data collection.
- Inspect topic query precision and recall manually.
- Add company-level signals and source diversity.
- Compare the transparent scorer with an LLM explanation layer without allowing the LLM to alter the numerical score.
