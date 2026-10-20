# Local AI Workbench - PowerShell Installation Script
$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       LOCAL AI WORKBENCH - INSTALLATION SCRIPT" -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Cyan

# 1. Check Python
Write-Host "[1/4] Checking Python environment..." -ForegroundColor Yellow
try {
    $pythonVer = python --version
    Write-Host "Found: $pythonVer" -ForegroundColor Green
} catch {
    Write-Error "Python was not found in PATH. Please install Python 3.10+."
    exit 1
}

# 2. Check Node & npm
Write-Host "`n[2/4] Checking Node.js and npm..." -ForegroundColor Yellow
try {
    $nodeVer = node --version
    $npmVer = npm --version
    Write-Host "Found: Node $nodeVer, npm $npmVer" -ForegroundColor Green
} catch {
    Write-Error "Node.js/npm not found. Please install Node.js 18+."
    exit 1
}

# 3. Install Backend Dependencies
Write-Host "`n[3/4] Installing backend Python packages..." -ForegroundColor Yellow
$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location "$rootDir\backend"
python -m pip install -r requirements.txt

# 4. Install Frontend & Build
Write-Host "`n[4/4] Installing frontend dependencies and compiling assets..." -ForegroundColor Yellow
Set-Location "$rootDir\frontend"
npm.cmd install --no-audit --no-fund
npm.cmd run build

Set-Location $rootDir
Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "  INSTALLATION COMPLETE! Run .\scripts\start.ps1 to start." -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Green
