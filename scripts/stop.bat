@echo off
echo [*] Stopping Local AI Workbench, Streamlit, ComfyUI, and Ollama instances...
powershell -NoProfile -Command "Get-Process -Name python, node, ollama -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*app.main*' -or $_.CommandLine -like '*backend\run.py*' -or $_.CommandLine -like '*streamlit*' -or $_.CommandLine -like '*ComfyUI\main.py*' -or $_.ProcessName -eq 'ollama' } | Stop-Process -Force"
echo [*] Local AI Workbench processes stopped.
