# Local AI Workbench - PowerShell Stop Script
$ErrorActionPreference = "SilentlyContinue"

Write-Host "[*] Stopping running Workbench, ComfyUI, and Ollama backend processes..." -ForegroundColor Yellow

$procs = Get-Process -Name python, node, ollama -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*app.main*" -or $_.CommandLine -like "*backend\run.py*" -or $_.CommandLine -like "*streamlit*" -or $_.CommandLine -like "*ComfyUI\main.py*" -or $_.ProcessName -eq "ollama"
}

if ($procs) {
    $procs | Stop-Process -Force
    Write-Host "[+] All Workbench, ComfyUI, and Ollama processes stopped successfully." -ForegroundColor Green
} else {
    Write-Host "[i] No active Workbench, ComfyUI, or Ollama processes were found." -ForegroundColor Gray
}
