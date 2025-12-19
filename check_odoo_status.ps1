# Script to check Odoo and database status
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ODOO STATUS CHECK" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check containers
Write-Host "[1/4] Checking containers..." -ForegroundColor Yellow
$Containers = docker ps --filter "name=odoo" --format "{{.Names}}\t{{.Status}}"
if ($Containers) {
    Write-Host "      Running containers:" -ForegroundColor Green
    $Containers | ForEach-Object {
        Write-Host "         $_" -ForegroundColor White
    }
} else {
    Write-Host "      ERROR: No Odoo containers running!" -ForegroundColor Red
    Write-Host "      Start with: docker compose up -d" -ForegroundColor Yellow
}

# Check database connection
Write-Host "[2/4] Checking database connection..." -ForegroundColor Yellow
$DbContainer = docker ps --filter "name=odoo_db" --format "{{.Names}}"
if ($DbContainer -eq "odoo_db") {
    $DbTest = docker exec odoo_db psql -U odoo -d odoo -c "SELECT version();" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      OK Database connection successful" -ForegroundColor Green
    } else {
        Write-Host "      ERROR: Cannot connect to database!" -ForegroundColor Red
        Write-Host "      Error: $DbTest" -ForegroundColor Red
    }
} else {
    Write-Host "      ERROR: Database container not running!" -ForegroundColor Red
}

# Check for ir_module_module table
Write-Host "[3/4] Checking for ir_module_module table..." -ForegroundColor Yellow
if ($DbContainer -eq "odoo_db") {
    $TableExists = docker exec odoo_db psql -U odoo -d odoo -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'ir_module_module');" 2>&1
    if ($TableExists -match "^\s*t\s*$") {
        Write-Host "      OK Table 'ir_module_module' exists" -ForegroundColor Green
        
        # Count modules
        $ModuleCount = docker exec odoo_db psql -U odoo -d odoo -t -c "SELECT COUNT(*) FROM ir_module_module;" 2>&1
        if ($ModuleCount -match "^\s*(\d+)\s*$") {
            Write-Host "      OK Found $($Matches[1]) modules in database" -ForegroundColor Green
        }
    } else {
        Write-Host "      ERROR: Table 'ir_module_module' does not exist!" -ForegroundColor Red
        Write-Host "      Database needs to be restored" -ForegroundColor Yellow
    }
} else {
    Write-Host "      SKIP: Database container not running" -ForegroundColor Yellow
}

# Check Odoo logs for errors
Write-Host "[4/4] Checking recent Odoo errors..." -ForegroundColor Yellow
$RecentErrors = docker compose logs --tail=50 odoo 2>&1 | Select-String -Pattern "ERROR|relation.*does not exist" -Context 0,2
if ($RecentErrors) {
    Write-Host "      WARNING: Found recent errors:" -ForegroundColor Yellow
    $RecentErrors | ForEach-Object {
        Write-Host "         $_" -ForegroundColor Red
    }
} else {
    Write-Host "      OK No recent errors found" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RECOMMENDATIONS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($TableExists -and $TableExists -notmatch "^\s*t\s*$") {
    Write-Host "1. Restore database using:" -ForegroundColor Yellow
    Write-Host "   .\restore_database_only.ps1 -BackupPath .\backup_YYYYMMDD_HHMMSS" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "2. Or check database status:" -ForegroundColor Yellow
    Write-Host "   .\check_database.ps1" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "3. View full logs:" -ForegroundColor Yellow
Write-Host "   docker compose logs -f odoo" -ForegroundColor Cyan

