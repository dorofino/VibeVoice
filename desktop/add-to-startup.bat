@echo off
cd /d "%~dp0.."
python -m desktop.create_shortcuts --startup
echo.
pause
