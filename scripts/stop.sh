#!/usr/bin/env bash
# ========================================================
#       LOCAL AI WORKBENCH - PROCESS TERMINATION SCRIPT
#       Supports macOS (Apple Silicon & Intel) & Linux
# ========================================================

echo "[*] Stopping Local AI Workbench, Streamlit, ComfyUI, and background services..."

# Gracefully terminate Streamlit
pkill -f "streamlit.*streamlit_app.py" 2>/dev/null && echo "[+] Stopped Streamlit runner." || true

# Gracefully terminate FastAPI / backend
pkill -f "backend/run.py" 2>/dev/null && echo "[+] Stopped backend runner." || true
pkill -f "uvicorn.*app.main:app" 2>/dev/null && echo "[+] Stopped uvicorn server." || true

# Gracefully terminate ComfyUI
pkill -f "ComfyUI/main.py" 2>/dev/null && echo "[+] Stopped ComfyUI service." || true

# Note about Ollama:
# We check if Ollama serve is running
if pgrep -f "ollama serve" >/dev/null 2>&1; then
    pkill -f "ollama serve" 2>/dev/null && echo "[+] Stopped Ollama background service." || true
fi

echo "[*] All Local AI Workbench processes stopped successfully."
