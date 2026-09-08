# FutureSearch External Baseline Integration Guide

## Overview

FutureSearch is an AI-powered forecasting service with a verifiable public track record. It can serve as an external baseline to compare against our transparent statistical scoring and GBDT models.

## Current Integration Barriers

1. **Python Version Incompatibility**
   - FutureSearch SDK requires Python 3.12+
   - Current project uses Python 3.11.9
   - Solution: Upgrade to Python 3.12+ or use a separate environment

2. **API Key and Cost**
   - Requires a paid API key
   - Pricing: ~$0.15 per question (LOW effort), ~$2 per question (HIGH effort)
   - For 6 topics × 31 windows = 186 questions × $0.15 = ~$27.9 (LOW mode)
   - Solution: Add `FUTURESEARCH_API_KEY` to `.env` and budget accordingly

3. **Async API Architecture**
   - All FutureSearch operations are coroutines (`async/await`)
   - Current pipeline is synchronous
   - Solution: Wrap calls in `asyncio.run()` or refactor to async

4. **Question Format Mismatch**
   - FutureSearch expects natural-language questions (YES/NO, numeric, date)
   - Our pipeline uses structured time-series data
   - Solution: Convert topic forecasts to questions, e.g.:
     - "Will large language models have higher academic publication count in 30 days compared to robotics?"
     - "What will the total GitHub activity be for AI agents in 30 days?"

## Integration Steps (Optional, for Future Work)

### 1. Environment Setup

```bash
# Upgrade Python to 3.12+ (outside the project venv)
pyenv install 3.12.0
pyenv local 3.12.0

# Create a separate venv for FutureSearch
python -m venv .venv-futuresearch
.venv-futuresearch/Scripts/activate

# Install FutureSearch SDK
pip install futuresearch
```

### 2. API Key Configuration

Add to `.env`:
```
FUTURESEARCH_API_KEY=sk-cho...
```

### 3. Question Formulation Helper

Create `Attempt/Shared/src/external_baselines/futuresearch_client.py`:

```python
"""FutureSearch client for external baseline forecasts."""

import asyncio
import pandas as pd
from typing import Any
from futuresearch.ops import forecast

async def forecast_topic_growth(
    topic_label: str,
    reference_topic: str,
    horizon_days: int,
    effort: str = "LOW",
) -> dict[str, Any]:
    """Ask FutureSearch whether topic A will outgrow topic B in horizon days.

    Returns: dict with probability, rationale, metadata.
    """
    question = f"""
    Will {topic_label} have higher combined academic, corporate, and community
    activity compared to {reference_topic} in the next {horizon_days} days?

    Sources to consider:
    - Academic: Crossref, OpenAlex, arXiv publication counts
    - Corporate: GDELT news/article counts
    - Community: GitHub stars, forks, activity

    Resolution criteria:
    - YES if the sum of normalized activity scores for {topic_label}
      exceeds that of {reference_topic} in the {horizon_days}-day window.
    - NO otherwise.
    """

    questions_df = pd.DataFrame([{
        "question": question,
        "resolution_criteria": f"Based on aggregated activity scores from Crossref, OpenAlex, arXiv, GDELT, and GitHub over the next {horizon_days} days.",
    }])

    result = await forecast(
        input=questions_df,
        forecast_type="binary",
        effort=effort,
    )

    return {
        "topic_label": topic_label,
        "reference_topic": reference_topic,
        "probability": result.data["probability"].iloc[0],
        "rationale": result.data["rationale"].iloc[0],
        "effort": effort,
    }
```

### 4. Batch Forecast Wrapper

```python
async def forecast_all_topics(
    topics: list[str],
    reference_topic: str = "robotics",
    horizon_days: int = 30,
) -> list[dict[str, Any]]:
    """Forecast all topics against a reference baseline."""
    tasks = [
        forecast_topic_growth(topic, reference_topic, horizon_days)
        for topic in topics
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### 5. Comparison with Internal Models

After obtaining FutureSearch forecasts, compare them with:
- Our transparent scoring (momentum-based)
- Our GBDT model predictions

Metrics:
- Rank correlation (Spearman) between FutureSearch and internal rankings
- MAE/RMSE on actual future activity (if available)

## Cost Estimation

For a full backtest (6 topics × 31 windows = 186 questions):
- LOW effort: 186 × $0.15 = $27.90
- HIGH effort: 186 × $2 = $372

Recommendation: Start with a subset (e.g., 3 topics × 6 windows = 18 questions) for validation.

## Current Recommendation

For the undergraduate research project, **do not integrate FutureSearch directly** because:

1. Cost barrier for full backtest (~$28 minimum)
2. Python version incompatibility (requires 3.12+)
3. Architectural complexity (async API)
4. Question formulation overhead for time-series data

Instead:
- Document FutureSearch as a known competitor/baseline
- Compare our transparent scoring against public benchmarks (Metaculus, ForecastBench)
- If budget allows, run a small subset comparison manually
- Focus on improving our internal models (GBDT, ensemble methods)

## References

- FutureSearch Python SDK: https://github.com/futuresearch/futuresearch-python
- Documentation: https://futuresearch.ai/docs
- Track record: https://evals.futuresearch.ai
- Pricing: ~$0.15 (LOW) / $2 (HIGH) per question
