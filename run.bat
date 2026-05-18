@echo off
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
