# Refresh all data for the project in .env and rebuild the dashboard.
# Usage (PowerShell, from anywhere):  & "<project folder>\refresh.ps1"
# Needs a valid login (py src\auth.py login). Read only: nothing is written to Forma.

Set-Location $PSScriptRoot
# Windows PowerShell 5.1 turns any stderr line from py (warnings, retries) into an error record,
# so success is judged by each step's exit code, not by error output.
$ErrorActionPreference = "Continue"

# One date for the whole run, so a refresh that crosses midnight keeps its files in one folder.
$env:SNAPSHOT_DAY = (Get-Date).ToString("yyyy-MM-dd")

$steps = @(
    "src\fetch\assets.py",
    "src\fetch\issues.py",
    "src\fetch\forms.py",
    "src\fetch\relationships.py",
    "src\fetch\documents.py",
    "src\fetch\models.py",
    "src\readiness.py",
    "src\render.py",
    "src\export_powerbi.py"
)

$started = Get-Date
foreach ($step in $steps) {
    Write-Host "== $step" -ForegroundColor Cyan
    py $step 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "$step failed (exit code $LASTEXITCODE). Fix it and run refresh.ps1 again." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
# If the Power BI project is open, load the new data into it too.
if (Get-Process PBIDesktop -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "Forma System Readiness*" }) {
    Write-Host "== Power BI" -ForegroundColor Cyan
    & "$PSScriptRoot\powerbi_refresh.ps1"
}
$seconds = [int]((Get-Date) - $started).TotalSeconds
Write-Host "Refresh done in $seconds s (snapshot $env:SNAPSHOT_DAY). Open the dashboard with .\serve.ps1, or data\powerbi\Forma System Readiness.pbip in Power BI Desktop" -ForegroundColor Green
