@echo off
if "%~1"=="" (
    echo Usage: restore.bat ^<backup_folder^>
    echo Example: restore.bat backup_20241114_112749
    pause
    exit /b 1
)
echo Running Odoo Restore...
powershell -ExecutionPolicy Bypass -File "%~dp0restore_odoo.ps1" -BackupPath "%~1"
pause

