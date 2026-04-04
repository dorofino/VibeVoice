@echo off
cd /d "%~dp0.."
python -m desktop.create_shortcuts --remove-startup
echo.
pause
