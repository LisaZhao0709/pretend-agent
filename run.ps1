<#
.SYNOPSIS
    一键运行数据采集和预测流水线（傻瓜版）
.DESCRIPTION
    自动激活虚拟环境，运行 CrossRef + GDELT 采集，生成预测报告。
    不需要记住任何路径或参数。
.PARAMETER Step
    要执行的步骤：all（默认，全流程）、collect（只采集）、score（只评分）、
    backtest（只回测）、check（只看数据状态）、test（只跑测试）
.PARAMETER AsOf
    快照日期 YYYY-MM-DD，默认今天
.EXAMPLE
    .\run.ps1                    # 全流程，用今天日期
    .\run.ps1 -Step collect      # 只采集数据
    .\run.ps1 -Step check        # 只看当前数据状态
    .\run.ps1 -Step test         # 只跑测试
    .\run.ps1 -Step all -AsOf 2026-08-20  # 全流程，指定日期
#>
param(
    [ValidateSet("all", "collect", "score", "backtest", "check", "test")]
    [string]$Step = "all",
    [string]$AsOf
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$AttemptRoot = Join-Path $ProjectRoot "Attempt"
$VenvPython = Join-Path $AttemptRoot ".venv\Scripts\python.exe"

# ========== 前置检查 ==========

if (-not (Test-Path $VenvPython)) {
    Write-Host "[错误] 找不到虚拟环境: $VenvPython" -ForegroundColor Red
    Write-Host "请先运行: powershell -ExecutionPolicy Bypass -File `"$AttemptRoot\scripts\setup_environment.ps1`""
    exit 1
}

if (-not $AsOf) {
    $AsOf = Get-Date -Format "yyyy-MM-dd"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Predictive Agents 一键运行" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  项目目录: $ProjectRoot"
Write-Host "  Python:   $VenvPython"
Write-Host "  日期:     $AsOf"
Write-Host "  步骤:     $Step"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========== 数据状态检查 ==========

function Show-DataStatus {
    Write-Host "--- 当前数据状态 ---" -ForegroundColor Yellow

    $dataRoot = Join-Path $ProjectRoot "Data"
    $interimDir = Join-Path $dataRoot "Interim\technology_cultivation_00"
    $reportDir = Join-Path $dataRoot "Reports\technology_cultivation_00"

    # CrossRef 缓存
    $crossrefCache = Join-Path $dataRoot "Raw\APIs\technology_cultivation_00\crossref"
    if (Test-Path $crossrefCache) {
        $crFiles = Get-ChildItem $crossrefCache -Filter "*.json" -ErrorAction SilentlyContinue
        Write-Host "  CrossRef 缓存: $($crFiles.Count) 个文件"
    } else {
        Write-Host "  CrossRef 缓存: 无（首次运行）"
    }

    # GDELT 缓存
    $gdeltCache = Join-Path $dataRoot "Raw\APIs\technology_cultivation_00\gdelt"
    if (Test-Path $gdeltCache) {
        $gdFiles = Get-ChildItem $gdeltCache -Filter "*.json" -ErrorAction SilentlyContinue
        Write-Host "  GDELT 缓存:   $($gdFiles.Count) 个文件"
    } else {
        Write-Host "  GDELT 缓存:   无"
    }

    # Interim 数据
    if (Test-Path $interimDir) {
        $interimFiles = Get-ChildItem $interimDir -Filter "*.jsonl" -ErrorAction SilentlyContinue
        Write-Host "  Interim 数据: $($interimFiles.Count) 个文件"
        foreach ($f in $interimFiles) {
            $lines = (Get-Content $f.FullName | Where-Object { $_.Trim() }).Count
            Write-Host "    $($f.Name): $lines 行"
        }
    } else {
        Write-Host "  Interim 数据: 无"
    }

    # 报告
    if (Test-Path $reportDir) {
        $reportFiles = Get-ChildItem $reportDir -ErrorAction SilentlyContinue
        Write-Host "  报告:         $($reportFiles.Count) 个文件"
    } else {
        Write-Host "  报告:         无"
    }

    Write-Host ""
}

# ========== 执行步骤 ==========

if ($Step -eq "check") {
    Show-DataStatus
    exit 0
}

if ($Step -eq "test") {
    Write-Host "--- 运行测试 ---" -ForegroundColor Yellow
    $forecastDir = Join-Path $AttemptRoot "Baselines\experiments\technology_cultivation_forecast_00"
    Push-Location $forecastDir
    try {
        & $VenvPython -m pytest tests/ -v
        $testExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($testExit -ne 0) { Write-Host "[测试失败]" -ForegroundColor Red; exit 1 }
    Write-Host "[测试通过]" -ForegroundColor Green
    exit 0
}

# forecast_00 实验路径
$forecastDir = Join-Path $AttemptRoot "Baselines\experiments\technology_cultivation_forecast_00"
$configPath = Join-Path $forecastDir "configs\forecast_00.yaml"

if (-not (Test-Path $configPath)) {
    Write-Host "[错误] 找不到配置文件: $configPath" -ForegroundColor Red
    exit 1
}

# --- 采集 ---
if ($Step -in @("all", "collect")) {
    Write-Host "--- 步骤 1/3: 数据采集 (CrossRef + GDELT) ---" -ForegroundColor Yellow
    Write-Host "  这可能需要几分钟，取决于 API 速率限制..." -ForegroundColor Gray
    Write-Host ""
    Push-Location $forecastDir
    try {
        & $VenvPython -m src.cli --config $configPath --mode collect --as-of $AsOf
        $collectExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($collectExit -ne 0) {
        Write-Host ""
        Write-Host "[警告] 采集过程中有错误（可能是 API 限流）" -ForegroundColor Yellow
        Write-Host "  已采集的数据已保存，可以稍后重试补全" -ForegroundColor Gray
        Write-Host "  运行 .\run.ps1 -Step check 查看已采集的数据量" -ForegroundColor Gray
    }
    Write-Host ""
    Show-DataStatus
    if ($Step -eq "collect") { exit 0 }
}

# --- 评分 ---
if ($Step -in @("all", "score")) {
    Write-Host "--- 步骤 2/3: 趋势评分 ---" -ForegroundColor Yellow
    Push-Location $forecastDir
    try {
        & $VenvPython -m src.cli --config $configPath --mode score --as-of $AsOf
        $scoreExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($scoreExit -ne 0) {
        Write-Host "[评分失败]" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
    if ($Step -eq "score") { exit 0 }
}

# --- 回测 ---
if ($Step -in @("all", "backtest")) {
    Write-Host "--- 步骤 3/3: 回测评估 ---" -ForegroundColor Yellow
    Push-Location $forecastDir
    try {
        & $VenvPython -m src.cli --config $configPath --mode backtest --as-of $AsOf
        $btExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($btExit -ne 0) {
        Write-Host "[回测失败]" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# ========== 完成 ==========

Write-Host "========================================" -ForegroundColor Green
Write-Host "  完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Show-DataStatus
Write-Host "报告位置: $ProjectRoot\Data\Reports\technology_cultivation_00\" -ForegroundColor Cyan
Write-Host ""
Write-Host "常用命令:" -ForegroundColor Gray
Write-Host "  .\run.ps1                  # 全流程"
Write-Host "  .\run.ps1 -Step collect    # 只采集"
Write-Host "  .\run.ps1 -Step check      # 看数据状态"
Write-Host "  .\run.ps1 -Step test       # 跑测试"
Write-Host ""
