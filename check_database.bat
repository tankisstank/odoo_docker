@echo off
echo Running Database Diagnostic...
powershell -ExecutionPolicy Bypass -File "%~dp0check_database.ps1"
pause

