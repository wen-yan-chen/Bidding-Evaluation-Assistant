# 一键重跑（PowerShell 7+）。会创建临时文档并在最后清理；不改代码/规则/YAML。
# 用法：powershell -File docs\评审功能测评数据\scripts\run_all.ps1
# 说明：pytest 会额外创建固定 doc_id 的测试产物，默认不跑；需要时加 -WithPytest。
param(
    [switch]$WithPytest,
    [switch]$SkipPerf
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $Root
$Base = "http://127.0.0.1:18080"
$Raw = "docs\评审功能测评数据\raw"
$Perf = "docs\评审功能测评数据\perf"
New-Item -ItemType Directory -Force $Raw, $Perf, "docs\screenshots" | Out-Null

function Run-Py([string]$Script) {
    Write-Host ">>> python $Script"
    python $Script
    if ($LASTEXITCODE -ne 0) { throw "失败：$Script" }
}

function Run-Compose([string]$Args) {
    Write-Host ">>> docker compose $Args"
    Invoke-Expression "docker compose $Args"
    if ($LASTEXITCODE -ne 0) { throw "失败：docker compose $Args" }
}

# 1) 官方门禁（只读/生成报告）
Run-Py "tools\validate_rules.py"
Run-Py "tools\validate_quotes.py"
Run-Compose 'run --rm --no-deps -v "$($PWD)\tools:/app/tools" -v "$($PWD)\data\samples:/app/data/samples" app python tools/eval_parse.py --strict'
Run-Compose 'run --rm --no-deps -v "$($PWD)\tools:/app/tools" -v "$($PWD)\data\samples:/app/data/samples" app python tools/eval_risks.py --strict'
python tools\smoke_test.py --base $Base | Tee-Object "$Raw\06-smoke_test.txt"

# 2) 独立准确性 / 边界 / 报告
Run-Py "docs\评审功能测评数据\scripts\run_accuracy.py"
Run-Py "docs\评审功能测评数据\scripts\postprocess.py"
Run-Py "docs\评审功能测评数据\scripts\run_edges.py"
Run-Py "docs\评审功能测评数据\scripts\run_boundary.py"
Run-Py "docs\评审功能测评数据\scripts\qual_semantics.py"
Run-Py "docs\评审功能测评数据\scripts\run_reports_all.py"
Run-Py "docs\评审功能测评数据\scripts\check_report_quotes.py"
Run-Py "docs\评审功能测评数据\scripts\make_ui_fixtures.py"

# 3) 性能（先重启 app 取冷启动；会清空 OCR 热缓存）
if (-not $SkipPerf) {
    docker compose restart app | Out-Null
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Milliseconds 1000
        try { if ((Invoke-RestMethod "$Base/health" -TimeoutSec 3).status -eq "ok") { break } } catch {}
    }
    Start-Sleep -Milliseconds 500
    Run-Py "docs\评审功能测评数据\scripts\run_perf.py"
    foreach ($i in 2, 3) {
        docker compose restart app | Out-Null
        for ($k = 0; $k -lt 60; $k++) {
            Start-Sleep -Milliseconds 1000
            try { if ((Invoke-RestMethod "$Base/health" -TimeoutSec 3).status -eq "ok") { break } } catch {}
        }
        Start-Sleep -Milliseconds 500
        python "docs\评审功能测评数据\scripts\run_cold.py" $i
    }
    Run-Py "docs\评审功能测评数据\scripts\run_ui_perf.py"
}

# 4) Playwright 页面
Run-Py "docs\评审功能测评数据\scripts\run_ui.py"
Run-Py "docs\评审功能测评数据\scripts\run_ui_reports.py"
Run-Py "docs\评审功能测评数据\scripts\run_ui_extra.py"

# 5) 可选的 pytest（会留下 20261115-abcdef01 测试产物，需再跑 cleanup）
if ($WithPytest) {
    Run-Compose 'run --rm --no-deps -v "$($PWD)\tests:/app/tests" app sh -c "pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple pytest httpx && python -m pytest -q"'
}

# 6) 清理本次测评创建的临时文档（保留原有数据）
Run-Py "docs\评审功能测评数据\scripts\cleanup.py"
Write-Host "完成。报告：docs\评审功能测评报告.md"
