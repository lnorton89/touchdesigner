<#
.SYNOPSIS
    Start the llama.cpp inference server for use with TouchDesigner LLM operators.
.DESCRIPTION
    Delegates to the llama project's start-server.ps1 launcher. The llama project
    manages model downloads, hardware profiles, and GPU configuration.
.PARAMETER LlamaProject
    Path to the llama project root containing scripts/server/start-server.ps1.
    Defaults to ..\llama relative to this script's location.
.PARAMETER Profile
    Named hardware/context profile from the llama project's profiles.yaml.
    See profiles.yaml for available profiles.
.PARAMETER Model
    Model name from profiles.yaml or a GGUF file path.
.PARAMETER Port
    Server listening port override.
.PARAMETER DryRun
    Print the resolved command without starting the server.
.EXAMPLE
    .\scripts\start-llama-server.ps1
    Start with the default profile (moe-balanced).
.EXAMPLE
    .\scripts\start-llama-server.ps1 -Profile moe-maxctx -DryRun
    Show what command would be used for 128K context mode.
#>
param(
    [string]$LlamaProject = "",
    [string]$Profile = "",
    [string]$Model = "",
    [int]$Port = 0,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Resolve llama project path
if (-not $LlamaProject) {
    $ScriptDir = Split-Path -Parent $PSScriptRoot
    $LlamaProject = Resolve-Path (Join-Path $ScriptDir "..\llama") -ErrorAction SilentlyContinue
    if (-not $LlamaProject) {
        # Fallback: known location
        $Candidate = "C:\Users\Lawrence\Documents\dev\llama"
        if (Test-Path $Candidate) {
            $LlamaProject = $Candidate
        } else {
            Write-Error "llama project not found. Specify -LlamaProject path or clone to sibling directory."
            exit 1
        }
    }
}

$Launcher = Join-Path $LlamaProject "scripts\server\start-server.ps1"
if (-not (Test-Path $Launcher)) {
    Write-Error "Launcher not found at: $Launcher"
    Write-Error "Ensure the llama project is set up at: $LlamaProject"
    exit 1
}

# Build args
$ArgsList = @()
if ($Profile) { $ArgsList += "-Profile"; $ArgsList += $Profile }
if ($Model) { $ArgsList += "-Model"; $ArgsList += $Model }
if ($Port -gt 0) { $ArgsList += "-Port"; $ArgsList += $Port }
if ($DryRun) { $ArgsList += "-DryRun" }

Write-Host "=== Starting llama.cpp server for TouchDesigner ===" -ForegroundColor Cyan
Write-Host "Project: $LlamaProject" -ForegroundColor Yellow
if ($ArgsList.Count -gt 0) {
    Write-Host "Args: $($ArgsList -join ' ')" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "The server exposes an OpenAI-compatible API at:" -ForegroundColor Green
Write-Host "  http://127.0.0.1:$($Port -gt 0 ? $Port : '8080')/v1" -ForegroundColor Green
Write-Host ""
Write-Host "Configure your Model Router with Provider = llama.cpp" -ForegroundColor Cyan
Write-Host ""

& $Launcher @ArgsList
