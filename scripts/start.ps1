# Local AI Workbench - PowerShell Start Script
$ErrorActionPreference = "Continue"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "         LOCAL AI WORKBENCH - LAUNCH SCRIPT" -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location $rootDir

# Set CUDA safety flags for Ollama
$env:OLLAMA_FLASH_ATTENTION = "false"

# Check & start local Ollama service
try {
    $ollama = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[+] Ollama server is ONLINE (Version: $($ollama.version))" -ForegroundColor Green
} catch {
    Write-Host "[*] Auto-starting local Ollama service..." -ForegroundColor Green
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
}

# Launch ComfyUI if present
if (Test-Path "$rootDir\ComfyUI\main.py") {
    try {
        $c = Invoke-WebRequest -Uri "http://127.0.0.1:8188/system_stats" -TimeoutSec 1 -ErrorAction Stop
        Write-Host "[+] ComfyUI server is already ONLINE" -ForegroundColor Green
    } catch {
        Write-Host "[*] Launching local ComfyUI image generator service alongside Ollama..." -ForegroundColor Green
        $hasCuda = python -c "import torch; print(torch.cuda.is_available())" 2>$null
        $extraArgs = if ($hasCuda -eq "True") { "" } else { "--cpu --use-split-cross-attention" }
        Start-Process python -ArgumentList "$rootDir\ComfyUI\main.py --listen 127.0.0.1 --port 8188 $extraArgs" -WorkingDirectory "$rootDir\ComfyUI" -WindowStyle Hidden
        Start-Sleep -Seconds 3
    }
}

Write-Host "`n[*] Starting Local AI Workbench at http://127.0.0.1:8000..." -ForegroundColor Green
Write-Host "[*] Opening browser..." -ForegroundColor Gray
Start-Process "http://127.0.0.1:8000"

python backend\run.py
