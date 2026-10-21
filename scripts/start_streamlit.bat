@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo        LOCAL AI WORKBENCH - STREAMLIT LAUNCHER
echo ========================================================
echo.

set ROOT_DIR=%~dp0..
cd /d "%ROOT_DIR%"

:: 1. Check Ollama reachability
echo [*] Checking local Ollama service...
powershell -NoProfile -Command "try { $v = (Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2).version; Write-Host '[+] Ollama connected! Version:' $v -ForegroundColor Green } catch { Write-Host '[!] Warning: Ollama is not running on http://127.0.0.1:11434. Start Ollama to enable AI chat.' -ForegroundColor Yellow }"

:: 2. Launch ComfyUI service if present
if exist "%ROOT_DIR%\ComfyUI\main.py" (
    echo [*] Checking ComfyUI service...
    powershell -NoProfile -Command "try { $c = Invoke-WebRequest -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 1 -ErrorAction Stop; Write-Host '[+] ComfyUI is already ONLINE!' -ForegroundColor Green } catch { Write-Host '[*] Auto-starting local ComfyUI alongside Ollama...' -ForegroundColor Green; Start-Process python -ArgumentList '%ROOT_DIR%\ComfyUI\main.py --listen 127.0.0.1 --port 8188 --cpu --use-split-cross-attention' -WorkingDirectory '%ROOT_DIR%\ComfyUI' -WindowStyle Hidden; Start-Sleep -Seconds 3 }"
)

:: 3. Launch Streamlit Application
echo.
echo [*] Starting Local AI Workbench via Streamlit at http://127.0.0.1:8501...
echo [*] Press Ctrl+C in this terminal window to stop the application.
echo.

python -m streamlit run streamlit_app.py --server.port 8501 --server.headless true
