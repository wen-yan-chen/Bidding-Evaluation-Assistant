# 把开发仓库同步到 AgentsHub fork 的提交目录，并（可选）提交 / 推送。
#
# 用法（在项目任意位置执行）：
#   pwsh tools/sync_to_agentshub.ps1                      # 只同步文件，看差异
#   pwsh tools/sync_to_agentshub.ps1 -Commit              # 同步 + 提交（消息取本仓库最新 commit 标题）
#   pwsh tools/sync_to_agentshub.ps1 -Commit -Push         # 同步 + 提交 + 推送
#   pwsh tools/sync_to_agentshub.ps1 -Message "..."        # 自定义提交消息
#   pwsh tools/sync_to_agentshub.ps1 -IncludeVideo         # 连 docs/video/*.mp4 一起同步（D10 用）
#
# 为什么要有这个脚本：开发在独立仓库（含 Dockerfile / api / web / tests），
# 提交目录只是其中一部分。手工复制必然漏文件（32 题就踩过 Dockerfile COPY api 却漏 api/ 的坑）。

[CmdletBinding()]
param(
    [string]$Repo = 'D:\contest-8\AgentsHub',
    [string]$AgentDir = '行业智能体\政务\招投标评审助手',
    [switch]$Commit,
    [switch]$Push,
    [string]$Message = '',
    [switch]$IncludeVideo
)

$ErrorActionPreference = 'Stop'
$Source = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Target = Join-Path $Repo $AgentDir

Write-Host "源目录 : $Source"
Write-Host "目标   : $Target"

if (-not (Test-Path (Join-Path $Repo '.git'))) {
    throw "目标不是 git 仓库：$Repo（先 clone fork：git clone --depth 1 <fork-url> $Repo）"
}

# 首次同步时目录还不存在，robocopy 会自己建
if (-not (Test-Path $Target)) {
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
    Write-Host "已新建提交目录：$AgentDir"
}

$excludeDirs = @(
    (Join-Path $Source '.git'),
    (Join-Path $Source '__pycache__'),
    (Join-Path $Source '.pytest_cache'),
    (Join-Path $Source '.mypy_cache'),
    (Join-Path $Source '.venv'),
    (Join-Path $Source 'data\uploads')      # 上传件是运行时产物，不入库
)
$excludeFiles = @('*.pyc', '*.log', '.DS_Store', 'Thumbs.db')
if (-not $IncludeVideo) { $excludeFiles += '*.mp4' }

$roboArgs = @($Source, $Target, '/MIR', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:1', '/W:1')
if ($excludeDirs.Count) { $roboArgs += '/XD'; $roboArgs += $excludeDirs }
if ($excludeFiles.Count) { $roboArgs += '/XF'; $roboArgs += $excludeFiles }

$null = robocopy @roboArgs
# robocopy 退出码 0-7 都算成功（0=无变化, 1=有复制, 2=有额外文件被删 …）
if ($LASTEXITCODE -ge 8) { throw "robocopy 失败，退出码 $LASTEXITCODE" }

# data/uploads 在目标里保留占位文件，保证目录结构一致
$uploads = Join-Path $Target 'data\uploads'
New-Item -ItemType Directory -Path $uploads -Force | Out-Null
$keep = Join-Path $uploads '.gitkeep'
if (-not (Test-Path $keep)) { New-Item -ItemType File -Path $keep | Out-Null }

Write-Host ''
Write-Host '--- 提交目录差异（git status）---'
$status = git -C $Repo status --short -- $AgentDir
if ($status) { $status } else { Write-Host '(无差异)' }
Write-Host ''

if (-not $Commit) {
    Write-Host '仅同步，未提交。确认无误后加 -Commit（可再 -Push）。'
    return
}

if (-not $Message) {
    $subject = (git -C $Source log -1 --pretty=%s) | Out-String
    $subject = $subject.Trim()
    if (-not $subject) { $subject = "sync $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }
    $Message = "kw8: $subject"
}

git -C $Repo add -- $AgentDir
if (-not (git -C $Repo diff --cached --name-only)) {
    Write-Host '没有需要提交的变更。'
    return
}
git -C $Repo commit -m $Message
Write-Host "已提交：$Message"

if ($Push) {
    git -C $Repo push -u origin HEAD
    Write-Host '已推送。'
} else {
    Write-Host "未推送。推送：git -C `"$Repo`" push -u origin HEAD"
}
