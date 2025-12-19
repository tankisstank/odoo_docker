# Script to restore all databases from custom-format backups (.dump)
param(
    [Parameter(Mandatory=$true)]
    [string]$BackupPath
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DATABASE RESTORE SCRIPT (CUSTOM FORMAT)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check prereqs
Write-Host "[1/4] Checking prerequisites..." -ForegroundColor Yellow
$DbContainer = "odoo_db"
$DbUser = "odoo"
$DatabasesDir = "$BackupPath\databases"

$ContainerCheck = docker ps --filter "name=$DbContainer" --format "{{.Names}}"
if ($ContainerCheck -ne $DbContainer) {
    Write-Host "      ERROR: Container '$DbContainer' is not running!" -ForegroundColor Red; exit 1
}
if (-not (Test-Path $DatabasesDir)) {
    Write-Host "      ERROR: Backup directory does not contain 'databases' folder." -ForegroundColor Red; exit 1
}
Write-Host "      OK Prerequisites met." -ForegroundColor Green

# Step 2: Restore globals
Write-Host "[2/4] Restoring globals (roles, users)..." -ForegroundColor Yellow
$GlobalsFile = "$DatabasesDir\globals.sql"
if (Test-Path $GlobalsFile) {
    Get-Content $GlobalsFile -Encoding UTF8 | docker exec -i $DbContainer psql -U $DbUser -d postgres
    Write-Host "      OK Globals restored." -ForegroundColor Green
} else {
    Write-Host "      WARNING: globals.sql not found, skipping." -ForegroundColor Yellow
}

# Step 3: Find databases to restore
Write-Host "[3/4] Finding databases to restore..." -ForegroundColor Yellow
$Databases = Get-ChildItem -Path $DatabasesDir -Filter "*.dump" -File | ForEach-Object { $_.BaseName }
if (-not $Databases) {
    Write-Host "      ERROR: No .dump files found in '$DatabasesDir'" -ForegroundColor Red; exit 1
}
Write-Host "      OK Found $($Databases.Count) database(s)." -ForegroundColor Green

# Step 4: Restore individual databases
Write-Host "[4/4] Restoring individual databases..." -ForegroundColor Yellow
foreach ($DbName in $Databases) {
    $LocalDumpFile = "$DatabasesDir\${DbName}.dump"
    $ContainerDumpFile = "/tmp/${DbName}.dump"
    Write-Host "      Processing: $DbName..." -ForegroundColor Cyan

    # A. Prepare DB
    Write-Host "         - Preparing database..." -ForegroundColor White
    docker exec $DbContainer psql -U $DbUser -d postgres -c "DROP DATABASE IF EXISTS $DbName;"
    docker exec $DbContainer psql -U $DbUser -d postgres -c "CREATE DATABASE $DbName;"

    # B. Copy backup file into container
    Write-Host "         - Copying backup to container..." -ForegroundColor White
    docker cp $LocalDumpFile "${DbContainer}:${ContainerDumpFile}"


    # C. Restore using pg_restore
    Write-Host "         - Restoring data with pg_restore..." -ForegroundColor White
    $RestoreCommand = "pg_restore -U $DbUser -d $DbName --clean --if-exists --verbose $ContainerDumpFile"
    $RestoreOutput = docker exec $DbContainer sh -c "$RestoreCommand"
    
    # D. Cleanup
    Write-Host "         - Cleaning up..." -ForegroundColor White
    docker exec $DbContainer rm $ContainerDumpFile

    if ($LASTEXITCODE -eq 0) {
        Write-Host "         - SUCCESS: Database '$DbName' restored." -ForegroundColor Green
    } else {
        Write-Host "         - WARNING: Database '$DbName' might have been restored with errors." -ForegroundColor Yellow
        Write-Host "           $RestoreOutput"
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RESTORE COMPLETED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart Odoo container: docker compose restart odoo" -ForegroundColor White