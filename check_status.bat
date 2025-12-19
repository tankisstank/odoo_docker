@echo off
echo Checking Odoo Status...
powershell -ExecutionPolicy Bypass -File "%~dp0check_odoo_status.ps1"
pause

