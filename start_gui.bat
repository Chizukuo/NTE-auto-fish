@echo off
REM Launch the GUI elevated. The target game often runs as administrator, and
REM Windows blocks synthetic key input from a lower integrity level — without
REM admin the on-screen tracker works but Pull Left/Right never register.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
where pythonw >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not found in PATH.
    echo Please install Python 3.11+ and check "Add Python to PATH".
    pause
    exit /b 1
)
start "" pythonw start_gui.py
