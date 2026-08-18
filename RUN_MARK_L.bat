@echo off
setlocal enabledelayedexpansion
title Mark-L
echo Starting Mark-L...

rem ---------------------------------------------------------------------------
rem Locate the app folder. INSTALL_AND_RUN.bat produces "Mark-L"; a hand-extracted
rem GitHub ZIP produces "Mark-L-main". Support both, plus running from inside.
rem ---------------------------------------------------------------------------
rem FIRST match wins — guard each check with "if not defined". Without the guard a
rem later line overwrites an earlier one, so when both folders exist the launcher
rem silently starts the wrong (older) copy.
set "APPDIR="
if not defined APPDIR if exist "%~dp0Mark-L\main.py"      set "APPDIR=%~dp0Mark-L"
if not defined APPDIR if exist "%~dp0Mark-L-main\main.py" set "APPDIR=%~dp0Mark-L-main"
if not defined APPDIR if exist "%~dp0main.py"             set "APPDIR=%~dp0"

if not defined APPDIR (
    echo.
    echo ERROR: Could not find main.py next to this launcher.
    echo.
    pause
    exit /b 1
)
cd /d "%APPDIR%"

rem ---------------------------------------------------------------------------
rem Pick an interpreter that ACTUALLY HAS the dependencies.
rem
rem This matters: on many machines "python" and "pip" resolve to DIFFERENT Python
rem installations. Bare `pip install` then succeeds while `python main.py` crashes
rem with ModuleNotFoundError, because the packages landed in the other interpreter.
rem So probe candidates and verify by import rather than trusting PATH order.
rem ---------------------------------------------------------------------------
set "PY="
for %%P in (
    "py -3.11"
    "py -3"
    "python"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
) do (
    if not defined PY (
        %%~P -c "import PyQt6, sounddevice, google.genai" >nul 2>&1
        if !errorlevel! equ 0 set "PY=%%~P"
    )
)

if not defined PY (
    echo.
    echo ================================================
    echo   Dependencies are not installed for any Python
    echo   found on this machine.
    echo ================================================
    echo.
    echo Fix it by running this ONE command, which installs into the
    echo same interpreter that will run the app:
    echo.
    echo     python -m pip install -r requirements.txt
    echo.
    echo ^(Use "python -m pip", never bare "pip" — bare pip can install
    echo  into a different Python than the one that launches Mark-L.^)
    echo.
    pause
    exit /b 1
)

echo Using interpreter: %PY%
%PY% main.py
if %errorlevel% neq 0 (
    echo.
    echo Mark-L exited with an error ^(code %errorlevel%^).
    echo.
)
pause
