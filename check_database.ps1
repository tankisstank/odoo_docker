# Script to check database status and tables
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DATABASE DIAGNOSTIC SCRIPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if database container is running
Write-Host "[1/5] Checking database container..." -ForegroundColor Yellow
$DbContainer = docker ps --filter "name=odoo_db" --format "{{.Names}}"
if ($DbContainer -eq "odoo_db") {
    Write-Host "      OK Container odoo_db is running" -ForegroundColor Green
} else {
    Write-Host "      ERROR: Container odoo_db is not running!" -ForegroundColor Red
    Write-Host "      Please start it: docker compose up -d db" -ForegroundColor Yellow
    exit 1
}

# Check if database exists
Write-Host "[2/5] Checking if database 'odoo' exists..." -ForegroundColor Yellow
$DbExists = docker exec odoo_db psql -U odoo -lqt | Select-String -Pattern "^\s*odoo\s"
if ($DbExists) {
    Write-Host "      OK Database 'odoo' exists" -ForegroundColor Green
} else {
    Write-Host "      ERROR: Database 'odoo' does not exist!" -ForegroundColor Red
    Write-Host "      Database needs to be created or restored" -ForegroundColor Yellow
}

# Check if database has tables
Write-Host "[3/5] Checking if database has tables..." -ForegroundColor Yellow
$TableCount = docker exec odoo_db psql -U odoo -d odoo -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>&1
if ($TableCount -match "^\s*(\d+)\s*$") {
    $Count = [int]$Matches[1]
    if ($Count -gt 0) {
        Write-Host "      OK Database has $Count tables" -ForegroundColor Green
    } else {
        Write-Host "      ERROR: Database has no tables!" -ForegroundColor Red
        Write-Host "      Database is empty - needs to be restored" -ForegroundColor Yellow
    }
} else {
    Write-Host "      ERROR: Cannot connect to database or database is empty" -ForegroundColor Red
    Write-Host "      Error: $TableCount" -ForegroundColor Red
}

# Check for critical Odoo tables
Write-Host "[4/5] Checking for critical Odoo tables..." -ForegroundColor Yellow
$CriticalTables = @("ir_module_module", "res_users", "res_partner", "sale_order")
$MissingTables = @()

foreach ($Table in $CriticalTables) {
    $Exists = docker exec odoo_db psql -U odoo -d odoo -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '$Table');" 2>&1
    if ($Exists -match "^\s*t\s*$") {
        Write-Host "      OK Table '$Table' exists" -ForegroundColor Green
    } else {
        Write-Host "      ERROR: Table '$Table' does not exist!" -ForegroundColor Red
        $MissingTables += $Table
    }
}

# Check if backup file exists
Write-Host "[5/5] Checking for database backup file..." -ForegroundColor Yellow
$BackupFiles = Get-ChildItem -Path "." -Filter "database_backup.sql" -Recurse -ErrorAction SilentlyContinue
if ($BackupFiles) {
    Write-Host "      OK Found database backup files:" -ForegroundColor Green
    foreach ($File in $BackupFiles) {
        $SizeMB = [math]::Round($File.Length / 1MB, 2)
        Write-Host "         - $($File.FullName) ($SizeMB MB)" -ForegroundColor White
    }
} else {
    Write-Host "      WARNING: No database_backup.sql found in current directory" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($MissingTables.Count -gt 0) {
    Write-Host "STATUS: Database needs to be restored" -ForegroundColor Red
    Write-Host ""
    Write-Host "Missing tables: $($MissingTables -join ', ')" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "SOLUTION:" -ForegroundColor Yellow
    Write-Host "1. Find your backup folder (e.g., backup_YYYYMMDD_HHMMSS)" -ForegroundColor White
    Write-Host "2. Restore database using:" -ForegroundColor White
    Write-Host "   Get-Content .\backup_YYYYMMDD_HHMMSS\database_backup.sql | docker exec -i odoo_db psql -U odoo odoo" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or run the restore script:" -ForegroundColor White
    Write-Host "   .\restore_odoo.ps1 -BackupPath .\backup_YYYYMMDD_HHMMSS -RestoreDatabase" -ForegroundColor Cyan
} else {
    Write-Host "STATUS: Database appears to be OK" -ForegroundColor Green
}

