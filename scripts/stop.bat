@echo off
echo [*] Stopping Local AI Workbench, Streamlit, and ComfyUI instances...
powershell -NoProfile -Command "Get-Process -Name python, node -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*app.main*' -or $_.CommandLine -like '*backend\run.py*' -or $_.CommandLine -like '*streamlit*' -or $_.CommandLine -like '*ComfyUI\main.py*' } | Stop-Process -Force"
echo [*] Local AI Workbench processes stopped.
