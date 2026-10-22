# Serve the dashboard on http://127.0.0.1:8765 (live 3D viewer included) and open it in the browser.
# Usage (PowerShell):  & "<project folder>\serve.ps1"   [-Port 9000]
# Stop with Ctrl+C. Listens on this computer only.

param([int]$Port = 8765)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Start-Job -ScriptBlock { param($p) Start-Sleep -Seconds 2; Start-Process "http://127.0.0.1:$p" } -ArgumentList $Port | Out-Null
py src\serve.py --port $Port
