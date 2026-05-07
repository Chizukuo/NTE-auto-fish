@echo off
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not found in PATH.
    echo Please install Python 3.11+ and check "Add Python to PATH".
    pause
    exit /b 1
)
python main.py %*
if %errorlevel% neq 0 pause
