# Script Backup Odoo Docker Environment
param(
    [string]$BackupPath = ".\backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')",
    [switch]$IncludeData = $true,
    [switch]$IncludeDatabase = $true
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ODOO DOCKER BACKUP SCRIPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Create backup directory
New-Item -ItemType Directory -Force -Path $BackupPath | Out-Null
Write-Host "[1/7] Created backup directory: $BackupPath" -ForegroundColor Green

# 1. Backup docker-compose.yml and Dockerfile
Write-Host "[2/7] Backing up Docker configuration..." -ForegroundColor Yellow
Copy-Item -Path ".\docker-compose.yml" -Destination "$BackupPath\docker-compose.yml" -Force
Copy-Item -Path ".\Dockerfile" -Destination "$BackupPath\Dockerfile" -Force
Write-Host "      OK docker-compose.yml" -ForegroundColor Green
Write-Host "      OK Dockerfile" -ForegroundColor Green

# 2. Backup custom_addons
Write-Host "[3/7] Backing up custom_addons..." -ForegroundColor Yellow
$CustomAddonsBackup = "$BackupPath\custom_addons"
New-Item -ItemType Directory -Force -Path $CustomAddonsBackup | Out-Null

Get-ChildItem -Path ".\custom_addons" -Directory | ForEach-Object {
    $ModuleName = $_.Name
    $SourcePath = $_.FullName
    $DestPath = "$CustomAddonsBackup\$ModuleName"
    robocopy $SourcePath $DestPath /E /XD __pycache__ /NFL /NDL /NJH /NJS /NC /NS /NP /R:3 /W:5 | Out-Null
    Write-Host "      OK $ModuleName" -ForegroundColor Green
}

# 3. Backup all databases
if ($IncludeDatabase) {
    Write-Host "[4/7] Backing up all databases (custom format)..." -ForegroundColor Yellow
    $DbBackupDir = "$BackupPath\databases"
    New-Item -ItemType Directory -Force -Path $DbBackupDir | Out-Null
    
    $DbContainer = "odoo_db" # Use container name directly
    $DbUser = "odoo"
    
    $ContainerCheck = docker ps --filter "name=$DbContainer" --format "{{.Names}}"
    if ($ContainerCheck -eq $DbContainer) {
        # Backup globals (roles, users, etc.) - This remains plain text
        Write-Host "      Backing up globals (roles, users)..." -ForegroundColor Yellow
        $GlobalsFile = "$DbBackupDir\globals.sql"
        docker exec $DbContainer pg_dumpall -U $DbUser -g --encoding=UTF8 | Out-File -FilePath $GlobalsFile -Encoding UTF8
        
        # Get list of all databases
        Write-Host "      Finding all databases..." -ForegroundColor Yellow
        $DbListCommand = "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres';"
        $Databases = docker exec $DbContainer psql -U $DbUser -t -c $DbListCommand | ForEach-Object { $_.Trim() } | Where-Object { $_ }

        if ($Databases) {
            Write-Host "      Found $($Databases.Count) database(s) to backup" -ForegroundColor Green
            foreach ($DbName in $Databases) {
                $ContainerDumpFile = "/tmp/${DbName}.dump"
                $LocalDumpFile = "$DbBackupDir\${DbName}.dump"
                Write-Host "      Backing up: $DbName to $LocalDumpFile..." -ForegroundColor Yellow
                
                $DumpCommand = "pg_dump -U $DbUser -d $DbName --encoding=UTF8 --format=custom --file=$ContainerDumpFile"
                docker exec $DbContainer sh -c "$DumpCommand"
                
                # Check if dump file was created inside container before copying
                $FileCheckCommand = "test -f $ContainerDumpFile && echo 'exists'"

                $FileExists = docker exec $DbContainer sh -c $FileCheckCommand
                
                if ($FileExists -match "exists") {
                    docker cp "${DbContainer}:${ContainerDumpFile}" $LocalDumpFile
                    docker exec $DbContainer rm $ContainerDumpFile
                    
                    if (Test-Path $LocalDumpFile) {
                        $SizeMB = [math]::Round((Get-Item $LocalDumpFile).Length / 1MB, 2)
                        Write-Host "         OK $DbName ($SizeMB MB)" -ForegroundColor Green
                    } else {
                        Write-Host "         ERROR: Failed to copy backup for $DbName from container." -ForegroundColor Red
                    }
                } else {
                    Write-Host "         ERROR: Failed to create backup for $DbName inside container." -ForegroundColor Red
                }
            }
        } else {
            Write-Host "      WARNING: No user databases found to backup" -ForegroundColor Yellow
        }
        
        $Databases | Out-File -FilePath "$DbBackupDir\databases_list.txt" -Encoding UTF8
    } else {
        Write-Host "      WARNING: Container '$DbContainer' not running, skipping database backup" -ForegroundColor Yellow
    }
} else {
    Write-Host "[4/7] Skipping database backup (--IncludeDatabase = false)" -ForegroundColor Yellow
}


# 4. Backup Odoo data
if ($IncludeData) {
    Write-Host "[5/7] Backing up Odoo data..." -ForegroundColor Yellow
    $OdooDataBackup = "$BackupPath\odoo_data"
    if (Test-Path ".\odoo_data\filestore") {
        Write-Host "      Copying filestore (this may take a while)..." -ForegroundColor Yellow
        robocopy ".\odoo_data\filestore" "$OdooDataBackup\filestore" /E /NFL /NDL /NJH /NJS /NC /NS /NP /R:3 /W:5 | Out-Null
        Write-Host "      OK Filestore" -ForegroundColor Green
    }
    if (Test-Path ".\odoo_data\sessions") {
        robocopy ".\odoo_data\sessions" "$OdooDataBackup\sessions" /E /NFL /NDL /NJH /NJS /NC /NS /NP /R:3 /W:5 | Out-Null
        Write-Host "      OK Sessions" -ForegroundColor Green
    }
} else {
    Write-Host "[5/7] Skipping Odoo data backup (--IncludeData = false)" -ForegroundColor Yellow
}

# 5. Backup other config files
Write-Host "[6/7] Backing up other config files..." -ForegroundColor Yellow
$ConfigFiles = @("README.md", "*.md", "*.py", "*.sql")
foreach ($Pattern in $ConfigFiles) {
    Get-ChildItem -Path "." -Filter $Pattern -File | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination "$BackupPath\$($_.Name)" -Force
        Write-Host "      OK $($_.Name)" -ForegroundColor Green
    }
}

# 6. Create backup info file
Write-Host "[7/7] Creating backup info file..." -ForegroundColor Yellow
$BackupDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$BackupInfo = "ODOO DOCKER BACKUP INFORMATION`r`n"
$BackupInfo += "================================`r`n"
$BackupInfo += "Backup Date: $BackupDate`r`n"
$BackupInfo += "Backup Path: $BackupPath`r`n`r`n"
$BackupInfo += "BACKUP CONTENTS:`r`n"
$BackupInfo += "- docker-compose.yml: Docker Compose configuration`r`n"
$BackupInfo += "- Dockerfile: Docker image configuration`r`n"
$BackupInfo += "- custom_addons/: All custom modules (excluding __pycache__)`r`n"
$BackupInfo += "- databases/: All databases backup (NEW FORMAT)`r`n"
$BackupInfo += "  * globals.sql: Database roles and users`r`n"
$BackupInfo += "  * databases_list.txt: List of all databases`r`n"
$BackupInfo += "  * <database_name>.sql: Individual database dumps`r`n"
$BackupInfo += "- database_backup.sql: Single database dump (OLD FORMAT, if exists)`r`n"
$BackupInfo += "- odoo_data/: Filestore and sessions (if available)`r`n"
$BackupInfo += "- Other config files: README, scripts, etc.`r`n`r`n"
$BackupInfo += "RESTORE INSTRUCTIONS:`r`n"
$BackupInfo += "1. Copy entire backup folder to new machine`r`n"
$BackupInfo += "2. Edit docker-compose.yml if needed (volume paths)`r`n"
$BackupInfo += "3. Restore all databases: .\restore_odoo.ps1 -BackupPath .\backup_folder`r`n"
$BackupInfo += "   Or restore databases only: .\restore_database_only.ps1 -BackupPath .\backup_folder`r`n"
$BackupInfo += "4. Start containers: docker compose up -d`r`n`r`n"
$BackupInfo += "NOTES:`r`n"
$BackupInfo += "- Ensure Docker and Docker Compose are installed`r`n"
$BackupInfo += "- Check ports and volumes in docker-compose.yml`r`n"
$BackupInfo += "- Default database password: odoo (should be changed in production)`r`n"

[System.IO.File]::WriteAllText("$BackupPath\BACKUP_INFO.txt", $BackupInfo, [System.Text.Encoding]::UTF8)
Write-Host "      OK BACKUP_INFO.txt" -ForegroundColor Green

# Calculate backup size
$BackupSize = (Get-ChildItem -Path $BackupPath -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BACKUP COMPLETED!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backup folder: $BackupPath" -ForegroundColor White
Write-Host "Size: $([math]::Round($BackupSize, 2)) MB" -ForegroundColor White
Write-Host ""
Write-Host "To restore, see file: $BackupPath\BACKUP_INFO.txt" -ForegroundColor Yellow

