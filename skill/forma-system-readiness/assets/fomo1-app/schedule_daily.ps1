# Registers a Windows scheduled task that refreshes the FOMO1 dashboard every morning.
# Usage (PowerShell, in this folder):   .\schedule_daily.ps1            (default 06:00)
#                                        .\schedule_daily.ps1 -Time 07:30
# Remove later with:  Unregister-ScheduledTask -TaskName "FOMO1 Daily Refresh"
param([string]$Time = "06:00")

$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
# Prefer the py launcher: on many Windows PCs "python" is only the Microsoft Store stub.
$python = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command python -ErrorAction Stop).Source }
if ($python -like "*WindowsApps*") { throw "Only the Microsoft Store python stub was found. Install Python from python.org (it adds the py launcher)." }

$action   = New-ScheduledTaskAction -Execute $python -Argument "`"$here\fomo1.py`" run" -WorkingDirectory $here
$trigger  = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName "FOMO1 Daily Refresh" -Action $action -Trigger $trigger -Settings $settings `
  -Description "FOMO1: pull Forma assets/issues/forms/relationships (read-only) and rebuild output\dashboard.html" -Force

Write-Host "Scheduled daily at $Time. Test now with:  Start-ScheduledTask -TaskName 'FOMO1 Daily Refresh'"
Write-Host "Log file: $here\output\logs\fomo1.log"
