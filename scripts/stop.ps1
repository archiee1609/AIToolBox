# Local AI Workbench - PowerShell Stop Script
$ErrorActionPreference = "SilentlyContinue"

Write-Host "[*] Stopping running Workbench and ComfyUI backend processes..." -ForegroundColor Yellow

$procs = Get-Process -Name python, node -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*app.main*" -or $_.CommandLine -like "*backend\run.py*" -or $_.CommandLine -like "*ComfyUI\main.py*"
}

if ($procs) {
    $procs | Stop-Process -Force
    Write-Host "[+] All Workbench and ComfyUI processes stopped successfully." -ForegroundColor Green
} else {
    Write-Host "[i] No active Workbench or ComfyUI processes were found." -ForegroundColor Gray
}
