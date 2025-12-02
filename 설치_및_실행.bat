@echo off
cd /d "%~dp0"
title Setup and Run

echo ========================================
echo   OncaPan Auto Comment Macro
echo   Setup and Run Script
echo ========================================
echo.

REM Check Python installation
echo [1/4] Checking Python installation...
set PYTHON_CMD=

python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :python_found
)

py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto :python_found
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    goto :python_found
)

echo.
echo [ERROR] Python is not installed or not in PATH!
echo.
echo Please install Python 3.11 or 3.12
echo Download: https://www.python.org/downloads/
echo.
echo Installation Notes:
echo   - Check "Add Python to PATH" option
echo   - Select "tcl/tk and IDLE" option
echo   - After installation, restart this script
echo.
pause
exit /b 1

:python_found
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python found: %PYTHON_CMD%
echo Python version: %PYTHON_VERSION%
echo.

REM Check Python version
%PYTHON_CMD% -c "import sys; exit(0 if sys.version_info < (3, 13) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Python 3.13+ may have compatibility issues.
    echo Python 3.11 or 3.12 is recommended for best compatibility.
    echo Some packages may need newer versions.
    echo.
    choice /C YN /M "Continue anyway"
    if errorlevel 2 exit /b 1
    echo.
)

REM Upgrade pip
echo [2/4] Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [WARNING] Failed to upgrade pip. Continuing...
) else (
    echo pip upgrade completed
)
echo.

REM Install packages
echo [3/4] Installing required packages...
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt file not found!
    pause
    exit /b 1
)

%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [WARNING] Some packages failed to install.
    echo Trying to install without strict version requirements...
    echo.
    %PYTHON_CMD% -m pip install requests beautifulsoup4 openai cryptography selenium webdriver-manager pyinstaller --upgrade
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install packages.
        echo Please check the error messages above.
        echo.
        pause
        exit /b 1
    )
)
echo Package installation completed
echo.

REM Run program
echo [4/4] Starting program...
echo.
echo ========================================
echo   Program is starting...
echo   This window will stay open to show errors.
echo   Close the window to exit.
echo ========================================
echo.

if not exist "main.py" (
    echo [ERROR] main.py file not found!
    echo.
    pause
    exit /b 1
)

echo Running: %PYTHON_CMD% main.py
echo.
%PYTHON_CMD% main.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ========================================
if %EXIT_CODE% NEQ 0 (
    echo   Program exited with error code: %EXIT_CODE%
    echo ========================================
    echo.
    echo An error occurred while running the program.
    echo.
    echo Please check the following files for details:
    echo   - error.log
    echo   - macro.log
    echo.
) else (
    echo   Program exited normally (code: %EXIT_CODE%)
    echo ========================================
    echo.
)
echo Press any key to close this window...
pause >nul
