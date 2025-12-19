# Helper script to run restore with proper execution policy
param(
    [Parameter(Mandatory=$true)]
    [string]$BackupPath
)

powershell -ExecutionPolicy Bypass -File .\restore_odoo.ps1 -BackupPath $BackupPath

