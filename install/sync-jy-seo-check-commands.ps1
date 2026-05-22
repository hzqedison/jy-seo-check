# sync-jy-seo-check-commands.ps1
# 由 install-skills.ps1 的 postInstall 调用：把 jy-seo-check 的斜杠命令同步到 .claude/commands/
# 安装方法：把本文件复制到目标仓库的 scripts/ 下，并在 .claude/skills.json 的 jy-seo-check 条目里
#           用 postInstall 引用它（script: sync-jy-seo-check-commands.ps1）。
param([string]$Root = (Split-Path $PSScriptRoot -Parent))

$src = Join-Path $Root ".claude\skills\jy-seo-check\commands\jy-seo-check.md"
$cmdDir = Join-Path $Root ".claude\commands"

if (-not (Test-Path $src)) {
    Write-Host "  [warn] jy-seo-check 尚未安装，跳过命令同步" -ForegroundColor Yellow
    return
}

New-Item -ItemType Directory -Force $cmdDir | Out-Null
Copy-Item $src (Join-Path $cmdDir "jy-seo-check.md") -Force
Write-Host "  [ok] /jy-seo-check 命令已同步到 .claude/commands/"
