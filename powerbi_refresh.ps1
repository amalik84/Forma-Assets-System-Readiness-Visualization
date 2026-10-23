# Refresh the open Power BI Desktop project from the latest CSVs, without clicking anything.
# Usage (PowerShell): .\powerbi_refresh.ps1   (Power BI Desktop must have "Forma System Readiness.pbip" open)
# Talks only to the local Power BI engine on this computer (localhost).

$ErrorActionPreference = "Stop"
$bin = "C:\Program Files\Microsoft Power BI Desktop\bin"
# LoadFrom instead of Add-Type: Add-Type stops on optional dependencies this script does not use.
[System.Reflection.Assembly]::LoadFrom((Join-Path $bin "Microsoft.PowerBI.AdomdClient.dll")) | Out-Null

$portFile = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces" -Recurse -Filter msmdsrv.port.txt -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $portFile) { throw "Power BI Desktop does not seem to be running. Open data\powerbi\Forma System Readiness.pbip first." }
$port = ([System.IO.File]::ReadAllText($portFile.FullName, [System.Text.Encoding]::Unicode)).Trim()

$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection "Data Source=localhost:$port"
$conn.Open()
$db = $conn.Database
if (-not $db) {
    $cmd = $conn.CreateCommand(); $cmd.CommandText = "SELECT [CATALOG_NAME] FROM `$SYSTEM.DBSCHEMA_CATALOGS"
    $r = $cmd.ExecuteReader(); if ($r.Read()) { $db = $r.GetString(0) }; $r.Close()
}
$cmd = $conn.CreateCommand()
$cmd.CommandText = '{"refresh": {"type": "full", "objects": [{"database": "' + $db + '"}]}}'
$cmd.ExecuteNonQuery() | Out-Null
$conn.Close()
Write-Host "Power BI data refreshed (local engine on port $port). Visuals update within a few seconds." -ForegroundColor Green
