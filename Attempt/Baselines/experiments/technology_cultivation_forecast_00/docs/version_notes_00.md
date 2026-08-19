# Version Notes 00

## 目标

建立第一个可运行的技术联合培养势能预测基线：分别估计学术研究活动和公司公开研发/产业布局活动，并生成联合排名。

## 本版变更

- 新建 OpenAlex 和 GDELT 的合规公开 API 适配器。
- 增加 User-Agent、请求间隔、Retry-After、指数退避、随机抖动和本地响应缓存。
- 采集失败项以 `collection_status: failed` 记录，避免把限流或超时误判成活动为零。
- 使用 6 个 15 天历史窗口，避免超出 GDELT 近 3 个月公开检索范围。
- 增加近期水平、增长、加速度、持续性和联合几何平均分。
- 增加 score 与 rolling backtest 命令。

## 数据和模型

- Data version: `technology_cultivation_00`
- Model: transparent statistical baseline
- LLM: not used for numerical ranking
- Forecast horizon: 30 days
- Initial topic set: 6 manually configured technology topics

## 运行命令

```powershell
Set-Location 'F:\Predictive agents\Attempt\Baselines\experiments\technology_cultivation_forecast_00'
python -m src.cli --config configs/forecast_00.yaml --mode collect --as-of YYYY-MM-DD
python -m src.cli --config configs/forecast_00.yaml --mode score --as-of YYYY-MM-DD
python -m src.cli --config configs/forecast_00.yaml --mode backtest --as-of YYYY-MM-DD
```

## 当前状态

- [x] Python environment verified with local Anaconda Python 3.13.9
- [x] Unit tests passed: 4 tests
- [ ] Controlled OpenAlex collection completed
- [ ] Controlled GDELT collection completed
- [ ] Ranking manually inspected
- [ ] Backtest report reviewed

当前真实数据采集尚未完成：OpenAlex 和 GDELT 均曾返回 HTTP 429，未将限流结果伪装为活动数据；缓存目录只保留了空的来源目录，没有生成虚假预测结果。

## 已知问题

- 当前候选主题由配置文件手工提供。
- 公司侧暂时使用 GDELT 新闻活动代理指标，还没有公司级实体识别、招聘、专利、融资和产品发布独立数据。
- 需要在真实数据采集后检查 OpenAlex 查询式的精确率、主题重叠和 GDELT 时间线返回格式。

## 下一步

完成受控采集，保存实际请求与结果摘要，运行回测，确认指标定义后再考虑加入记忆或 LLM 解释层。
