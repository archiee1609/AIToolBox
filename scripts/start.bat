@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo          LOCAL AI WORKBENCH - LAUNCH SCRIPT
echo ========================================================
echo.

set ROOT_DIR=%~dp0..
cd /d "%ROOT_DIR%"

:: Set CUDA safety flags for Ollama
set OLLAMA_FLASH_ATTENTION=false

:: 1. Check & start local Ollama service
echo [*] Checking local Ollama service...
powershell -NoProfile -Command "try { $v = (Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2).version; Write-Host '[+] Ollama is ONLINE! Version:' $v -ForegroundColor Green } catch { Write-Host '[*] Auto-starting local Ollama service...' -ForegroundColor Green; Start-Process ollama -ArgumentList 'serve' -WindowStyle Hidden -ErrorAction SilentlyContinue; Start-Sleep -Seconds 3 }"

:: 2. Launch ComfyUI service if present
if exist "%ROOT_DIR%\ComfyUI\main.py" (
    echo [*] Launching local ComfyUI image generator service alongside Ollama...
    start "ComfyUI Server" /min cmd /c "cd /d %ROOT_DIR%\ComfyUI && python main.py --listen 127.0.0.1 --port 8188 --cpu --use-split-cross-attention"
    timeout /t 3 /nobreak >nul
)

:: 3. Check ComfyUI reachability
echo [*] Checking local ComfyUI service...
powershell -NoProfile -Command "try { $c = Invoke-WebRequest -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 2; Write-Host '[+] ComfyUI service connected on http://127.0.0.1:8188!' -ForegroundColor Green } catch { Write-Host '[i] Info: ComfyUI is starting up or idle. Workbench will auto-manage it.' -ForegroundColor Cyan }"

:: 4. Launch Backend & Open Browser
echo.
echo [*] Starting Local AI Workbench server at http://127.0.0.1:8000...
echo [*] Press Ctrl+C in this terminal window to stop the application.
echo.

start "" "http://127.0.0.1:8000"
python backend\run.py
