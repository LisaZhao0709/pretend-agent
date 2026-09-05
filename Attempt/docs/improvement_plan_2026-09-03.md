# Predictive Agents 完善计划

> 创建日期：2026-09-03
> 状态：待用户确认
> 基于：竞品调研（2026-09-02）+ 项目现状诊断

## 一、现状诊断

### 数据层问题清单

| # | 问题 | 严重度 | 现状 |
|---|------|--------|------|
| D1 | OpenAlex 禁用，学术信号仅靠 Crossref | 高 | Crossref `query` 是全文搜索，结果可能过于宽泛 |
| D2 | GitHub 信号已采集但未纳入评分 | 高 | `DataAnalysisAgent` 把 GitHub 列加入 pivot，但 `scoring.py` 只用 crossref+gdelt |
| D3 | GitHub 采集不区分主题 | 高 | 搜索 `created:>=D-7` 无 topic query，6 个主题的 GitHub 活动无法区分 |
| D4 | 无专利数据源 | 中 | TrendIntel/TrendOS 都用 USPTO 专利作为关键上游信号 |
| D5 | 无 arXiv/Semantic Scholar | 中 | Crossref 覆盖已发表论文，但预印本趋势更早 |
| D6 | 6 个主题手工配置，无自动发现 | 中 | 竞品用 BERTopic 聚类自动发现新兴主题 |
| D7 | 数据预处理仅有 merge+pivot+coverage 统计 | 高 | 缺少异常值检测、信号平滑、跨源标准化、时间对齐验证 |
| D8 | 采集需手动运行 CLI | 中 | 无定时/自动化采集调度 |
| D9 | GDELT 仅月度聚合，丢失日度粒度 | 低 | 日度数据可用于短期趋势检测，但当前 30 天预测窗口不需要 |
| D10 | 无数据清洗规则 | 高 | API 错误、空响应、异常计数未被过滤 |

### 架构问题清单

| # | 问题 | 严重度 |
|---|------|--------|
| A1 | PredictionAgent 和 ReportAgent 未实现 | 高 |
| A2 | 评分仅用 4 特征（level/growth/acceleration/persistence）| 中 |
| A3 | 无 LLM 集成 | 中（用户说可以是黑盒） |
| A4 | 无外部基线对比 | 中 |
| A5 | Memory_Design 和 Reasoning_Architecture 为空 | 低（用户说暂缓） |

---

## 二、完善计划（按优先级）

### Phase 1：数据层补全（当前优先）

#### 1.1 修复/替代学术数据源（解决 D1、D5）

**方案 A：修复 OpenAlex**
- 当前 OpenAlex collector 用 `search` + `per_page=1` + `meta.count`，这和失败的 `group_by` 方式不同
- 需要验证：免费额度是否够用（OpenAlex 每月 10k 请求免费，6 主题 × 31 月 = 186 请求，足够）
- 如果 credits paywall 仍然阻止，尝试用 `filter` 而非 `search`

**方案 B：增加 arXiv API**
- arXiv API 完全免费，无限制
- 覆盖预印本，比 Crossref（已发表）更早发现趋势
- 用 `search` + 日期过滤获取计数

**方案 C：增加 Semantic Scholar API**
- 免费学术搜索 API
- 可作为 Crossref 的交叉验证源

**建议**：先验证 OpenAlex 是否可用（方案 A），同时加 arXiv（方案 B）作为预印本信号。

#### 1.2 GitHub 主题化采集 + 纳入评分（解决 D2、D3）

**当前问题**：
- GitHub collector 搜索 `created:>=D-7` 不带 topic query
- 6 个主题共享同一批 repo，无法区分

**改进**：
- 给 GitHub 搜索加 topic query：`"{topic_keyword}" created:>=D-7`
- 在 `scoring.py` 增加 `github_score` 维度
- 联合评分从 2 维（academic+corporate）扩展到 3 维（academic+corporate+community）

**受影响文件**：
- `Shared/src/data_collectors/github.py` — 加 topic query
- `Baselines/.../scoring.py` — 增加 github_score
- `configs/forecast_00.yaml` — 增加 github 权重配置
- `configs/sources.yaml` — GitHub topic query 映射

#### 1.3 增加专利数据源（解决 D4）

**选项**：
- USPTO PatentsView API（免费，覆盖美国专利）
- Google Patents（无官方 API，需爬虫）
- lens.org API（需注册）

**建议**：USPTO PatentsView，免费且有 REST API。按 CPC 分类码或关键词搜索专利申请计数。

#### 1.4 数据预处理/清洗/筛选完善（解决 D7、D10）

**需要新增的预处理步骤**：

1. **异常值检测**：
   - 检测 activity_count 异常高/低的点（如 >3σ 或 =0）
   - 标记但不删除，由配置决定是否过滤

2. **信号平滑**：
   - 可选的移动中位数平滑（比移动平均更抗异常值）
   - 配置控制是否启用

3. **跨源标准化**：
   - 不同源计数尺度差异巨大（Crossref ~1000，GDELT ~10000，GitHub ~100）
   - 当前 scoring 用 min-max 归一化，但对异常值敏感
   - 改用 robust scaling（中位数 + IQR）或 rank-based 归一化

4. **时间对齐验证**：
   - 检查所有源是否覆盖相同的时间窗口
   - 标记缺失窗口并决定填充策略（前向填充/插值/置零）

5. **数据清洗规则**：
   - 过滤 `collection_status == "failed"` 的记录
   - 过滤 `activity_count is None` 的记录
   - 检测并标记连续零值（可能是 API 问题而非真实零活动）

**新增文件**：
- `Shared/src/processors/cleaner.py` — 数据清洗
- `Shared/src/processors/detector.py` — 异常值检测
- 更新 `Shared/src/processors/normalize.py` — 增加标准化方法

#### 1.5 自动化采集调度（解决 D8）

**方案**：
- 增加 `scripts/scheduled_collect.py` 脚本
- 用 Windows Task Scheduler 或简单 cron-like 循环
- 每次采集后自动更新 metadata

---

### Phase 2：多维预测模型（用户说可以是黑盒）

#### 2.1 多维特征矩阵

将当前 4 特征 × 2 源扩展为：

| 维度 | 数据源 | 特征 |
|------|--------|------|
| 学术 | Crossref + arXiv + OpenAlex | 论文计数、增长率、加速度、持续性、引用量（如有）|
| 新闻 | GDELT | 事件计数、增长率、加速度、持续性 |
| 社区 | GitHub | repo 新增数、stars 增量、forks 增量、活跃度 |
| 专利 | USPTO | 专利申请计数、增长率 |

#### 2.2 黑盒预测模型选项

| 模型 | 优点 | 缺点 |
|------|------|------|
| 随机森林/GBDT | 处理非线性、特征重要性可解释 | 需要足够样本 |
| LSTM/Transformer | 时序建模能力强 | 数据量可能不够 |
| 简单 ensemble | 透明、低计算量 | 可能欠拟合 |
| LLM 推理 | 可利用世界知识 | 成本高、不可复现 |

**建议**：先用 GBDT（如 LightGBM）作为黑盒基线，特征重要性可解释，计算量低。

#### 2.3 外部 AI 基线（解决 A4）

- 用 FutureSearch Python SDK 对同样 6 个主题做预测
- 对比本项目评分排名与 FutureSearch 预测概率
- 记录在 `Baselines/experiments/` 下

---

### Phase 3：评测体系完善

#### 3.1 内部回测增强
- 滚动时间切分 + 多指标（MAE/MAPE/RMSE + 排名准确率 + Top-K 命中率）
- 分主题、分源、分时间窗口的细粒度报告

#### 3.2 外部基线对比
- FutureSearch SDK 预测对比
- 可选：Metaculus 提交

---

## 三、受影响文件汇总

### Phase 1
| 文件 | 变更类型 |
|------|----------|
| `Shared/src/data_collectors/openalex.py` | 验证/修复 |
| `Shared/src/data_collectors/arxiv.py` | **新增** |
| `Shared/src/data_collectors/github.py` | 修改（加 topic query） |
| `Shared/src/data_collectors/uspto.py` | **新增** |
| `Shared/src/data_collectors/base.py` | 可能扩展（支持日度采集） |
| `Shared/src/processors/cleaner.py` | **新增** |
| `Shared/src/processors/detector.py` | **新增** |
| `Shared/src/processors/normalize.py` | 修改（增加标准化方法） |
| `Shared/src/processors/quality_checker.py` | 修改（增加清洗规则检查） |
| `Shared/src/config.py` | 修改（增加新源配置字段） |
| `configs/sources.yaml` | 修改（增加 arxiv/uspto 配置） |
| `configs/topics.yaml` | 修改（增加 github_query/arxiv_query 字段） |
| `Baselines/.../scoring.py` | 修改（增加 github_score 维度） |
| `Baselines/.../configs/forecast_00.yaml` | 修改（增加新源权重） |
| `scripts/scheduled_collect.py` | **新增** |

### Phase 2
| 文件 | 变更类型 |
|------|----------|
| `Reasoning_Architecture/experiments/...` | **新增**（多维预测模型实验） |
| `Baselines/experiments/external_baseline_futuresearch/` | **新增** |

---

## 四、风险

1. **API 限流**：新增 arXiv + USPTO 会增加请求数，需要合理设置间隔
2. **数据对齐**：不同源的时间粒度不同（Crossref 月度、GDELT 日度、GitHub 日度、USPTO 月度），需要统一窗口
3. **特征维度灾难**：从 4 特征扩展到 20+ 特征，6 主题 × 31 月 = 186 样本可能不够训练复杂模型
4. **主题查询精度**：GitHub/arXiv 加 topic query 后，查询精度需要人工验证
5. **专利数据延迟**：专利从申请到公开有 18 个月延迟，作为"早期信号"可能不如预期

## 五、验证计划

1. 每个新数据源 collector 写单元测试（mock API 响应）
2. 数据预处理每个步骤写测试（异常值检测、标准化、清洗）
3. 端到端测试：采集 → 清洗 → 评分 → 对比基线
4. 人工验证：抽查各源各主题的计数合理性
5. 回测对比：新评分 vs 旧评分的排名变化

## 六、建议执行顺序

1. **1.2 GitHub 主题化 + 纳入评分**（改动最小，收益最高——已有数据没用）
2. **1.4 数据预处理/清洗**（基础设施，后续都依赖）
3. **1.1 学术源修复/增加 arXiv**（提升学术信号质量）
4. **1.3 专利数据源**（扩展信号维度）
5. **Phase 2 多维预测模型**（数据层完善后）
6. **Phase 3 评测 + 外部基线**（模型完成后）
