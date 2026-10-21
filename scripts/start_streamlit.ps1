# Local AI Workbench - Streamlit PowerShell Launch Script
$ErrorActionPreference = "Continue"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       LOCAL AI WORKBENCH - STREAMLIT LAUNCHER" -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location $rootDir

# 1. Check Ollama reachability
try {
    $ollama = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[+] Ollama server is ONLINE (Version: $($ollama.version))" -ForegroundColor Green
} catch {
    Write-Host "[!] Warning: Ollama is not running on http://127.0.0.1:11434. Start Ollama to enable AI chat." -ForegroundColor Yellow
}

# 2. Launch ComfyUI service if present
if (Test-Path "$rootDir\ComfyUI\main.py") {
    try {
        $c = Invoke-WebRequest -Uri "http://127.0.0.1:8188/system_stats" -TimeoutSec 1 -ErrorAction Stop
        Write-Host "[+] ComfyUI server is already ONLINE" -ForegroundColor Green
    } catch {
        Write-Host "[*] Auto-starting local ComfyUI alongside Ollama..." -ForegroundColor Green
        Start-Process python -ArgumentList "$rootDir\ComfyUI\main.py --listen 127.0.0.1 --port 8188 --cpu --use-split-cross-attention" -WorkingDirectory "$rootDir\ComfyUI" -WindowStyle Hidden
        Start-Sleep -Seconds 3
    }
}

Write-Host "`n[*] Starting Local AI Workbench via Streamlit at http://127.0.0.1:8501..." -ForegroundColor Green
Write-Host "[*] Opening browser..." -ForegroundColor Gray
Start-Process "http://127.0.0.1:8501"

python -m streamlit run streamlit_app.py --server.port 8501 --server.headless true
