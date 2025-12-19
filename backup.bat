@echo off
echo Running Odoo Backup...
powershell -ExecutionPolicy Bypass -File "%~dp0backup_odoo.ps1" %*
pause

