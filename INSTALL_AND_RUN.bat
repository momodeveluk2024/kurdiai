@echo off
title Mark-L One-Click Installer
color 0A
echo ================================================
echo           Mark-L One-Click Installer
echo ================================================
echo.
echo This will automatically install everything you need:
echo - Download Mark-L repository
echo - Install Python dependencies
echo - Setup configuration
echo - Run the application
echo.
echo Press any key to continue...
pause >nul
cls

echo.
echo [1/6] Checking for Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed!
    echo.
    echo Please install Python 3.11 or 3.12 from:
    echo https://www.python.org/downloads/
    echo.
    echo During installation, make sure to check:
    echo "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo ✓ Python is installed
python --version

echo.
echo [2/6] Checking for Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Git not found. Downloading Mark-L as ZIP instead...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/FatihMakes/Mark-L/archive/refs/heads/main.zip' -OutFile 'Mark-L.zip'"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to download Mark-L
        pause
        exit /b 1
    )
    echo Extracting files...
    powershell -Command "Expand-Archive -Path 'Mark-L.zip' -DestinationPath '.' -Force"
    move Mark-L-main Mark-L >nul 2>&1
    del Mark-L.zip
    cd Mark-L
) else (
    echo ✓ Git is installed
    echo.
    echo [3/6] Downloading Mark-L repository...
    if exist Mark-L (
        echo Mark-L folder already exists, updating...
        cd Mark-L
        git pull
    ) else (
        echo Cloning repository...
        git clone https://github.com/FatihMakes/Mark-L.git Mark-L
        cd Mark-L
    )
)

echo ✓ Mark-L downloaded successfully
cd /d "%~dp0Mark-L"

echo.
echo [4/6] Installing Python dependencies...
echo This may take a few minutes...
rem Use "python -m pip", NOT bare "pip". On many machines they resolve to different
rem Python installations, so bare pip reports success while main.py then crashes
rem with ModuleNotFoundError because the packages went to the other interpreter.
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

rem Verify by import rather than trusting pip's exit code.
python -c "import PyQt6, sounddevice, google.genai" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Dependencies installed, but this Python cannot import them.
    echo Your "python" and "pip" commands point at different Python versions.
    echo.
    python -c "import sys; print('  python is:', sys.executable)"
    echo.
    echo Re-run this installer from a Command Prompt where both match.
    pause
    exit /b 1
)
echo ✓ Dependencies installed and verified

echo.
echo [5/6] Setting up configuration...
if not exist "config" mkdir config
echo.
echo ================================================
echo           IMPORTANT: Gemini API Key Required
echo ================================================
echo.
echo Mark-L requires a FREE Gemini API key to work.
echo.
echo To get your API key:
echo 1. Go to: https://makersuite.google.com/app/apikey
echo 2. Sign in with your Google account
echo 3. Click "Create API Key"
echo 4. Copy your API key
echo.

rem Read the key WITHOUT echoing it. "set /p" prints every character to the console,
rem which leaves a live API key sitting in the scrollback and in any screenshot.
for /f "delims=" %%K in ('powershell -NoProfile -Command "$s = Read-Host -AsSecureString 'Paste your Gemini API key here (input is hidden)'; [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))"') do set "API_KEY=%%K"

if not defined API_KEY (
    echo ERROR: No API key entered.
    pause
    exit /b 1
)

rem os_system is required too — the app's _check_config treats a config without it
rem as unconfigured and re-runs first-time setup on every launch.
echo {"gemini_api_key": "%API_KEY%", "os_system": "Windows"}> config\api_keys.json
set "API_KEY="

echo ✓ Configuration saved
echo.
echo [6/6] Starting Mark-L...
echo.
echo ================================================
echo.
echo Mark-L is now running!
echo.
echo To run Mark-L again in the future, just:
echo 1. Double-click: RUN_MARK_L.bat
echo.
echo ================================================

python main.py

pause
