# GitHub Integration & Multi-Agent Architecture Summary

## Completed Milestones

### M0 — Configuration & Storage Layout ✓
- Added `GITHUB_TOKEN` placeholder to `.env.example`
- Created `configs/sources.yaml` with per-source switches and GitHub parameters:
  - `k_new=100`: Top-K for newly created repos (last 7 days)
  - `k_active=50`: Top-K for recently active repos (pushed in last 1 day)
  - `delta_7d_threshold=100`: Star surge threshold
  - `use_llm_summarize=false`: LLM summarization gated (default off)
  - Optional language/org whitelists

### M1 — GitHub Client ✓
**File**: `Shared/src/tools/github_client.py`

Features:
- Dual-window search: new repos (created ≥D-7) + active repos (pushed ≥D-1)
- Automatic token type detection (Bearer for fine-grained, token for classic)
- Rate limiting: 0.4s auth, 1.5s unauth; exponential backoff on 429/403
- Caching: raw API responses in `Data/Raw/APIs/.../github/`
- Minimal record extraction: 15 key fields (repo_id, full_name, stars, forks, language, etc.)
- Derived signals: stars_total, stars_per_day_lifetime, forks_total, activity_recent
- Output: two JSONL snapshots per day:
  - `github_repos_YYYY-MM-DD.jsonl`: minimal repo metadata
  - `github_signals_YYYY-MM-DD.jsonl`: derived metrics + created_at for month extraction

### M2 — Unified Search Tool ✓
**File**: `Shared/src/tools/search_tool.py`

- Single `search()` function routing to openalex/gdelt/github
- Loads `sources.yaml` for GitHub parameters (k_new, k_active, whitelists)
- Returns normalized records with schema: source, topic_id, topic_label, window_start, window_end, activity_count, features
- GitHub adapter: aggregates daily snapshots into monthly windows

### M3 — DataCollectionAgent ✓
**File**: `Shared/src/agents/data_collection_agent.py`

- Orchestrates multi-source collection for all topics
- Loads sources.yaml to enable/disable sources
- Accumulates records by source and persists to interim:
  - `openalex_records.jsonl`
  - `gdelt_records.jsonl`
- Outputs `collection_report.json` with per-topic, per-source counts and errors

### M4 — DataAnalysisAgent ✓
**File**: `Shared/src/agents/data_analysis_agent.py`

- Loads collected records from interim
- Merges OpenAlex + GDELT via existing `normalize.py`
- Extends pivot table with GitHub columns:
  - `github_stars_total`
  - `github_stars_per_day`
  - `github_forks_total`
  - `github_activity_recent`
- Runs data quality checks (coverage per source, missing windows, low-coverage topics)
- Outputs:
  - `pivot_table_extended.jsonl`: merged pivot with all sources
  - `quality_report.json`: coverage metrics and issues per topic

### M5 — Base Agent & Infrastructure ✓
**Files**: 
- `Shared/src/agents/__init__.py`
- `Shared/src/agents/base_agent.py`
- `Shared/src/tools/__init__.py`

- Simple base class for future agents
- AgentResult dataclass for consistent return format

## Test Results

### GitHub Fetch (Standalone)
```
15 repos fetched (10 new + 5 active)
Signals: stars_total, stars_per_day_lifetime, forks_total, activity_recent
Cached in: Data/Interim/technology_cultivation_00/github_signals_2026-08-17.jsonl
```

### Full Agent Pipeline
```
Phase 1: DataCollectionAgent
  - GDELT: 30 records per topic (5 topics = 150 total)
  - GitHub: 1 record per topic (5 topics = 5 total)
  - OpenAlex: 400 errors (rate-limited; will retry later)

Phase 2: DataAnalysisAgent
  - Pivot records: 150 (30 months × 5 topics)
  - Quality score: 23/100 (GDELT + GitHub coverage; OpenAlex missing)
  - Extended pivot: github_* columns populated for 2023-02 onwards
```

## Data Flow

```
GitHub API
  ↓ (fetch_github_trending)
Data/Raw/APIs/.../github/*.json (cached)
  ↓ (extract_minimal_repo)
Data/Interim/.../github_repos_YYYY-MM-DD.jsonl
  ↓ (derive signals)
Data/Interim/.../github_signals_YYYY-MM-DD.jsonl
  ↓ (DataAnalysisAgent._load_github_signals)
  ↓ (merge with OpenAlex/GDELT)
Data/Processed/.../pivot_table_extended.jsonl
  ↓ (quality_checker)
Data/Reports/.../quality_report.json
```

## Configuration Example

**configs/sources.yaml**:
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
    llm_daily_cap: 30
    description_max_chars: 280
    language_whitelist: []
    org_whitelist: []
```

## Token Setup

1. Create Personal Access Token (no org account required):
   - GitHub → Settings → Developer settings → Personal access tokens
   - Classic token: scope `public_repo`
   - Fine-grained token: Metadata: Read, Contents: Read

2. Add to Attempt/.env:
   ```
   GITHUB_TOKEN=ghp_xxx_or_github_pat_xxx
   ```

3. Verify:
   ```powershell
   $env:GITHUB_TOKEN = 'your_token'
   Invoke-RestMethod -Uri 'https://api.github.com/rate_limit' `
     -Headers @{ 'Authorization' = 'token ' + $env:GITHUB_TOKEN; 'User-Agent'='PredictiveAgents/0.1' } `
   | ConvertTo-Json -Depth 5
   ```
   - Expected: core.limit ≥ 5000 (vs. 60 unauth)

## Test Scripts

- **test_agents.py**: Runs DataCollectionAgent + DataAnalysisAgent
- **test_full_pipeline.py**: Full pipeline including forecast + report (in progress)

## Next Steps (M5+)

1. **Fix OpenAlex 400 errors**: Investigate date format or query syntax
2. **Repo Labeling**: Implement rules-first + LLM-fallback labeler (aspect, summary_short)
3. **PredictionAgent**: Research optimal data source combinations and algorithm selection
4. **ReportAgent**: Extend report_generator.py to include GitHub insights (top trending repos)
5. **Scheduling**: Daily run script and Windows Task Scheduler integration
6. **Optional**: StackOverflow, HackerNews, PatentsView integrations (pluggable)

## Known Issues

- OpenAlex API returning 400 errors (likely date filter format); GDELT + GitHub working
- GitHub signals currently use created_at for month extraction; consider using snapshot date for more precise daily aggregation
- Quality score low (23/100) due to OpenAlex failures; will improve once fixed

## Files Modified/Created

### New Files
- `Shared/src/tools/__init__.py`
- `Shared/src/tools/github_client.py`
- `Shared/src/tools/search_tool.py`
- `Shared/src/agents/__init__.py`
- `Shared/src/agents/base_agent.py`
- `Shared/src/agents/data_collection_agent.py`
- `Shared/src/agents/data_analysis_agent.py`
- `Shared/src/processors/quality_checker.py`
- `configs/sources.yaml`
- `Baselines/experiments/2026-08-14_simple_baseline/src/test_agents.py`
- `Baselines/experiments/2026-08-14_simple_baseline/src/test_full_pipeline.py`

### Modified Files
- `.env.example`: Added GITHUB_TOKEN placeholder
- `Shared/src/tools/github_client.py`: Added created_at to signals for month extraction

## Architecture Notes

- **Separation of concerns**: tools (API clients) → agents (orchestration) → processors (normalization)
- **Configuration-driven**: sources.yaml enables/disables sources and tunes parameters
- **Extensible**: new sources can be added as new tools + adapters in search_tool.py
- **Caching**: all API responses cached locally to avoid redundant requests
- **Error handling**: graceful degradation (one source failure doesn't block others)
