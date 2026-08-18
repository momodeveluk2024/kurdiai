@echo off
echo Creating Desktop Shortcut for Mark-L...
set "shortcutPath=%USERPROFILE%\Desktop\Mark-L.lnk"
set "targetPath=%~dp0RUN_MARK_L.bat"
set "workingDir=%~dp0"

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%shortcutPath%'); $s.TargetPath = '%targetPath%'; $s.WorkingDirectory = '%workingDir%'; $s.Description = 'Launch Mark-L AI Assistant'; $s.Save()"

if %errorlevel% equ 0 (
    echo.
    echo ✓ Desktop shortcut created successfully!
    echo.
    echo You can now launch Mark-L by double-clicking the
    echo "Mark-L" icon on your desktop.
    echo.
) else (
    echo.
    echo ✗ Failed to create desktop shortcut.
    echo You can still run Mark-L by double-clicking:
    echo RUN_MARK_L.bat
    echo.
)

pause
