@echo off
REM Double-click launcher for the TAK Device Monitor.
REM Starts the backend and opens the dashboard in your browser.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
