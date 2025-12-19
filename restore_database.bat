@echo off
if "%~1"=="" (
    echo Usage: restore_database.bat ^<backup_folder^>
    echo Example: restore_database.bat backup_20241114_112749
    pause
    exit /b 1
)
echo Running Database Restore...
powershell -ExecutionPolicy Bypass -File "%~dp0restore_database_only.ps1" -BackupPath "%~1"
pause

