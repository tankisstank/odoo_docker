# Script to fix volume paths in docker-compose.yml after restore
param(
    [string]$DockerComposeFile = ".\docker-compose.yml"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FIX DOCKER COMPOSE VOLUME PATHS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $DockerComposeFile)) {
    Write-Host "ERROR: docker-compose.yml not found!" -ForegroundColor Red
    exit 1
}

# Get current directory
$CurrentDir = (Get-Location).Path
Write-Host "Current directory: $CurrentDir" -ForegroundColor White
Write-Host ""

# Read docker-compose.yml
$Content = Get-Content $DockerComposeFile -Raw
$OriginalContent = $Content

# Fix absolute paths to relative paths
$Content = $Content -replace '"[A-Z]:\\[^"]+\\postgres_data:', "`"./postgres_data:"
$Content = $Content -replace '"[A-Z]:\\[^"]+\\odoo_data:', "`"./odoo_data:"

# Check if changes were made
if ($Content -ne $OriginalContent) {
    # Backup original file
    $BackupFile = "$DockerComposeFile.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $DockerComposeFile $BackupFile
    Write-Host "Backup created: $BackupFile" -ForegroundColor Green
    
    # Write fixed content
    [System.IO.File]::WriteAllText($DockerComposeFile, $Content, [System.Text.Encoding]::UTF8)
    Write-Host "Fixed volume paths in docker-compose.yml" -ForegroundColor Green
    Write-Host ""
    Write-Host "Changes made:" -ForegroundColor Yellow
    Write-Host "- Changed absolute paths to relative paths (./postgres_data, ./odoo_data)" -ForegroundColor White
} else {
    Write-Host "No changes needed. Paths are already correct." -ForegroundColor Green
}

Write-Host ""
Write-Host "Next step: docker compose up -d" -ForegroundColor Cyan

