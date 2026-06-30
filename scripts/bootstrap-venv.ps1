<#
.SYNOPSIS
    Create or verify an external Python virtual environment for TouchDesigner LLM operators.
.DESCRIPTION
    Creates a Python 3.11 virtual environment at the configured path and installs
    the dependencies from requirements.txt. TD loads packages from this venv via
    startup path injection rather than installing into TD's embedded Python.
.PARAMETER VenvPath
    Path to create the virtual environment. Defaults to .venv in the project root.
.PARAMETER Python
    Path to the Python 3.11 executable. If not provided, searches for python3.11
    or python in PATH and verifies the version.
.PARAMETER Force
    Delete and recreate an existing venv.
.PARAMETER SkipInstall
    Create the venv but skip pip install (for setup-only use).
.EXAMPLE
    .\scripts\bootstrap-venv.ps1
    Create .venv with Python 3.11 and install dependencies.
.EXAMPLE
    .\scripts\bootstrap-venv.ps1 -VenvPath C:\td-llm-venv -Force
    Create or recreate venv at a custom location.
#>
param(
    [string]$VenvPath = "",
    [string]$Python = "",
    [switch]$Force,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $VenvPath) { $VenvPath = Join-Path $ProjectRoot ".venv" }

# ── Resolve Python 3.11 ────────────────────────────────────────────
function Resolve-Python311 {
    $candidates = @($Python)
    if (-not $candidates -or -not $candidates[0]) {
        $candidates = @("python3.11", "python3", "python")
    }
    foreach ($exe in $candidates) {
        try {
            $ver = & $exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($ver -and $ver -ge 3.11) {
                return (Get-Command $exe).Source
            }
        } catch { continue }
    }
    return $null
}

$PythonExe = Resolve-Python311
if (-not $PythonExe) {
    Write-Error "Python 3.11+ not found. Install Python 3.11 from python.org or specify -Python."
    exit 1
}

Write-Host "Python: $PythonExe" -ForegroundColor Cyan
$pyVer = & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
Write-Host "Version: $pyVer" -ForegroundColor Cyan

# ── Create venv ─────────────────────────────────────────────────────
if (Test-Path $VenvPath) {
    if ($Force) {
        Write-Host "Removing existing venv at $VenvPath..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $VenvPath
    } else {
        $activate = Join-Path $VenvPath "Scripts\Activate.ps1"
        if (Test-Path $activate) {
            Write-Host "Venv already exists at $VenvPath (use -Force to recreate)" -ForegroundColor Green
            if (-not $SkipInstall) {
                $pip = Join-Path $VenvPath "Scripts\pip.exe"
                & $pip install -r (Join-Path $ProjectRoot "requirements.txt")
            }
            Write-Host "=== Done ===" -ForegroundColor Green
            exit 0
        }
        Write-Host "Path exists but is not a valid venv. Recreating..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $VenvPath
    }
}

Write-Host "Creating venv at $VenvPath..." -ForegroundColor Yellow
& $PythonExe -m venv $VenvPath
if (-not $?) { Write-Error "Failed to create venv"; exit 1 }

if (-not $SkipInstall) {
    $pip = Join-Path $VenvPath "Scripts\pip.exe"
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    & $pip install -r (Join-Path $ProjectRoot "requirements.txt")
    if (-not $?) { Write-Error "pip install failed"; exit 1 }
}

Write-Host "=== Venv ready: $VenvPath ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. In TouchDesigner, add this to a startup script (Text DAT):" -ForegroundColor Cyan
Write-Host "     import sys; sys.path.insert(0, r'$((Join-Path $VenvPath \"Lib\site-packages\").Replace('\','\\'))')"
Write-Host "  2. Or use: python $((Join-Path $ProjectRoot \"scripts\setup-td-path.py\").Replace('\','\\')) -VenvPath $(($VenvPath).Replace('\','\\'))"
