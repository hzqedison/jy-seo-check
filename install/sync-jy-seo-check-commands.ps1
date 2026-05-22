# sync-jy-seo-check-commands.ps1
# Called by install-skills.ps1 postInstall: sync the /jy-seo-check slash command to .claude/commands/
# Install: copy this file into the target repo's scripts/ and reference it in .claude/skills.json's
#          jy-seo-check entry via postInstall (script: sync-jy-seo-check-commands.ps1).
# (ASCII-only on purpose: avoids Windows PowerShell 5.1 UTF-8 parsing issues.)
param([string]$Root = (Split-Path $PSScriptRoot -Parent))

$src = Join-Path $Root ".claude\skills\jy-seo-check\commands\jy-seo-check.md"
$cmdDir = Join-Path $Root ".claude\commands"

if (-not (Test-Path $src)) {
    Write-Host "  [warn] jy-seo-check not installed yet, skip command sync" -ForegroundColor Yellow
    return
}

New-Item -ItemType Directory -Force $cmdDir | Out-Null
Copy-Item $src (Join-Path $cmdDir "jy-seo-check.md") -Force
Write-Host "  [ok] /jy-seo-check command synced to .claude/commands/"
