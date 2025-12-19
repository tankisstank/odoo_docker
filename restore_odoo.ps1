# Script Restore Odoo Docker Environment
param(
    [Parameter(Mandatory=$true)]
    [string]$BackupPath,
    [switch]$RestoreDatabase = $true,
    [switch]$RestoreData = $true
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ODOO DOCKER RESTORE SCRIPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if backup directory exists
if (-not (Test-Path $BackupPath)) {
    Write-Host "ERROR: Backup directory does not exist: $BackupPath" -ForegroundColor Red
    exit 1
}

Write-Host "Backup directory: $BackupPath" -ForegroundColor White
Write-Host ""

# 1. Restore docker-compose.yml and Dockerfile
Write-Host "[1/5] Restoring Docker configuration..." -ForegroundColor Yellow
if (Test-Path "$BackupPath\docker-compose.yml") {
    Copy-Item -Path "$BackupPath\docker-compose.yml" -Destination ".\docker-compose.yml" -Force
    Write-Host "      OK docker-compose.yml" -ForegroundColor Green
    
    # Fix volume paths (change absolute paths to relative paths)
    Write-Host "      Fixing volume paths..." -ForegroundColor Yellow
    $Content = Get-Content ".\docker-compose.yml" -Raw
    $Content = $Content -replace '"[A-Z]:\\[^"]+\\postgres_data:', "`"./postgres_data:"
    $Content = $Content -replace '"[A-Z]:\\[^"]+\\odoo_data:', "`"./odoo_data:"
    [System.IO.File]::WriteAllText(".\docker-compose.yml", $Content, [System.Text.Encoding]::UTF8)
    Write-Host "      OK Volume paths fixed" -ForegroundColor Green
} else {
    Write-Host "      ERROR: docker-compose.yml not found" -ForegroundColor Red
}

if (Test-Path "$BackupPath\Dockerfile") {
    Copy-Item -Path "$BackupPath\Dockerfile" -Destination ".\Dockerfile" -Force
    Write-Host "      OK Dockerfile" -ForegroundColor Green
} else {
    Write-Host "      ERROR: Dockerfile not found" -ForegroundColor Red
}

# 2. Restore custom_addons
Write-Host "[2/5] Restoring custom_addons..." -ForegroundColor Yellow
if (Test-Path "$BackupPath\custom_addons") {
    if (-not (Test-Path ".\custom_addons")) {
        New-Item -ItemType Directory -Force -Path ".\custom_addons" | Out-Null
    }
    
    Get-ChildItem -Path "$BackupPath\custom_addons" -Directory | ForEach-Object {
        $ModuleName = $_.Name
        $DestPath = ".\custom_addons\$ModuleName"
        
        if (Test-Path $DestPath) {
            Remove-Item -Path $DestPath -Recurse -Force
        }
        
        Copy-Item -Path $_.FullName -Destination $DestPath -Recurse -Force
        Write-Host "      OK $ModuleName" -ForegroundColor Green
    }
} else {
    Write-Host "      ERROR: custom_addons not found" -ForegroundColor Red
}

# 3. Restore all databases
if ($RestoreDatabase) {
    Write-Host "[3/5] Restoring all databases..." -ForegroundColor Yellow
    
    # Check if container is running
    $DbContainer = docker ps --filter "name=odoo_db" --format "{{.Names}}"
    if ($DbContainer -ne "odoo_db") {
        Write-Host "      WARNING: Container odoo_db is not running. Please start it first:" -ForegroundColor Yellow
        Write-Host "        docker compose up -d db" -ForegroundColor White
        Write-Host "[3/5] Skipping database restore" -ForegroundColor Yellow
    } else {
        # Check for new format (databases folder) or old format (single file)
        $DatabasesDir = "$BackupPath\databases"
        $OldBackupFile = "$BackupPath\database_backup.sql"
        
        if (Test-Path $DatabasesDir) {
            # New format: restore all databases from databases folder
            Write-Host "      Found databases folder (new format)..." -ForegroundColor Green
            
            # Restore globals first (roles, users)
            $GlobalsFile = "$DatabasesDir\globals.sql"
            if (Test-Path $GlobalsFile) {
                Write-Host "      Restoring globals (roles, users)..." -ForegroundColor Yellow
                Get-Content $GlobalsFile | docker exec -i odoo_db psql -U odoo 2>&1 | Out-Null
                Write-Host "      OK Globals restored" -ForegroundColor Green
            }
            
            # Get list of databases to restore
            $DbListFile = "$DatabasesDir\databases_list.txt"
            if (Test-Path $DbListFile) {
                $Databases = Get-Content $DbListFile | Where-Object { $_.Trim() -ne "" }
            } else {
                # If no list file, find all .sql files in databases folder
                $Databases = Get-ChildItem -Path $DatabasesDir -Filter "*.sql" -File | Where-Object { $_.Name -ne "globals.sql" } | ForEach-Object { $_.BaseName }
            }
            
            if ($Databases) {
                Write-Host "      Found $($Databases.Count) database(s) to restore" -ForegroundColor Green
                foreach ($DbName in $Databases) {
                    $DbBackupFile = "$DatabasesDir\${DbName}.sql"
                    if (Test-Path $DbBackupFile) {
                        Write-Host "      Restoring database: $DbName..." -ForegroundColor Yellow
                        
                        # Create database if it doesn't exist
                        $DbExists = docker exec odoo_db psql -U odoo -lqt | Select-String -Pattern "^\s+$DbName\s"
                        if (-not $DbExists) {
                            Write-Host "         Creating database $DbName..." -ForegroundColor Yellow
                            docker exec odoo_db psql -U odoo -c "CREATE DATABASE $DbName;" 2>&1 | Out-Null
                        }
                        
                        # Restore database
                        Get-Content $DbBackupFile | docker exec -i odoo_db psql -U odoo -d $DbName 2>&1 | Out-Null
                        if ($LASTEXITCODE -eq 0) {
                            Write-Host "         OK $DbName restored" -ForegroundColor Green
                        } else {
                            Write-Host "         WARNING: $DbName restore completed with errors" -ForegroundColor Yellow
                        }
                    } else {
                        Write-Host "         WARNING: Backup file not found for $DbName" -ForegroundColor Yellow
                    }
                }
            } else {
                Write-Host "      WARNING: No databases found to restore" -ForegroundColor Yellow
            }
        } elseif (Test-Path $OldBackupFile) {
            # Old format: restore single database_backup.sql
            Write-Host "      Found old format backup (database_backup.sql)..." -ForegroundColor Yellow
            Write-Host "      Restoring database 'odoo'..." -ForegroundColor Yellow
            
            # Create database if it doesn't exist
            $DbExists = docker exec odoo_db psql -U odoo -lqt | Select-String -Pattern "^\s+odoo\s"
            if (-not $DbExists) {
                Write-Host "         Creating database odoo..." -ForegroundColor Yellow
                docker exec odoo_db psql -U odoo -c "CREATE DATABASE odoo;" 2>&1 | Out-Null
            }
            
            Get-Content $OldBackupFile | docker exec -i odoo_db psql -U odoo -d odoo 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "      OK Database 'odoo' restored successfully" -ForegroundColor Green
            } else {
                Write-Host "      WARNING: Database restore completed with errors" -ForegroundColor Yellow
            }
        } else {
            Write-Host "      WARNING: No database backup found (neither databases folder nor database_backup.sql)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "[3/5] Skipping database restore (--RestoreDatabase = false)" -ForegroundColor Yellow
}

# 4. Restore Odoo data
if ($RestoreData) {
    Write-Host "[4/5] Restoring Odoo data..." -ForegroundColor Yellow
    if (Test-Path "$BackupPath\odoo_data") {
        if (-not (Test-Path ".\odoo_data")) {
            New-Item -ItemType Directory -Force -Path ".\odoo_data" | Out-Null
        }
        
        if (Test-Path "$BackupPath\odoo_data\filestore") {
            Write-Host "      Copying filestore (this may take a while)..." -ForegroundColor Yellow
            robocopy "$BackupPath\odoo_data\filestore" ".\odoo_data\filestore" /E /NFL /NDL /NJH /NJS /NC /NS /NP /R:3 /W:5 | Out-Null
            Write-Host "      OK Filestore" -ForegroundColor Green
        }
        
        if (Test-Path "$BackupPath\odoo_data\sessions") {
            robocopy "$BackupPath\odoo_data\sessions" ".\odoo_data\sessions" /E /NFL /NDL /NJH /NJS /NC /NS /NP /R:3 /W:5 | Out-Null
            Write-Host "      OK Sessions" -ForegroundColor Green
        }
    } else {
        Write-Host "      WARNING: odoo_data not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "[4/5] Skipping Odoo data restore (--RestoreData = false)" -ForegroundColor Yellow
}

# 5. Restore other files
Write-Host "[5/5] Restoring other config files..." -ForegroundColor Yellow
Get-ChildItem -Path $BackupPath -File | Where-Object {
    $_.Name -notmatch "BACKUP_INFO|database_backup"
} | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination ".\$($_.Name)" -Force
    Write-Host "      OK $($_.Name)" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RESTORE COMPLETED!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Check and edit docker-compose.yml if needed" -ForegroundColor White
Write-Host "2. Start containers: docker compose up -d" -ForegroundColor White
Write-Host "3. Check logs: docker compose logs -f" -ForegroundColor White
