@echo off
REM Self-elevate: the target game often runs as administrator, and Windows
REM blocks synthetic key input from a lower integrity level. Without admin the
REM on-screen tracker works but Pull Left/Right never register.
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process -FilePath '%~f0' -ArgumentList '%*' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not found in PATH.
    echo Please install Python 3.11+ and check "Add Python to PATH".
    pause
    exit /b 1
)
python main.py %*
if %errorlevel% neq 0 (
    echo.
    echo If this is your first run, install dependencies with:
    echo   python -m pip install -r requirements.txt
    pause
)
