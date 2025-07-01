@echo off
REM Todo Editor Universal Launcher
REM Replaces all individual batch files with a single launcher

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

REM Default to editor mode if no argument provided
if "%1"=="" (
    set "MODE=editor"
) else (
    set "MODE=%1"
)

REM Handle different launch modes
if /i "%MODE%"=="editor" (
    echo Starting Todo Editor...
    python todo_app.py editor
    goto :end
)

if /i "%MODE%"=="silent" (
    REM Start silently (minimized to tray)
    start "" pythonw todo_app.py editor --minimized
    goto :end
)

if /i "%MODE%"=="wallpaper" (
    echo Starting Wallpaper Generator...
    python todo_app.py wallpaper
    goto :end
)

if /i "%MODE%"=="setup" (
    echo Running Complete Setup...
    python todo_app.py setup
    goto :end
)

if /i "%MODE%"=="config" (
    echo Showing Configuration...
    python todo_app.py config
    pause
    goto :end
)

if /i "%MODE%"=="uninstall" (
    echo Uninstalling Todo Editor...
    python todo_app.py uninstall
    pause
    goto :end
)

if /i "%MODE%"=="help" (
    echo.
    echo Todo Editor Launcher
    echo ====================
    echo.
    echo Usage: todo.bat [mode]
    echo.
    echo Modes:
    echo   editor     - Start Todo Editor (default)
    echo   silent     - Start minimized to system tray
    echo   wallpaper  - Start wallpaper generator only
    echo   setup      - Run complete setup
    echo   config     - Show configuration
    echo   uninstall  - Remove shortcuts
    echo   help       - Show this help
    echo.
    echo Examples:
    echo   todo.bat                  - Start editor
    echo   todo.bat silent           - Start in background
    echo   todo.bat setup            - First time setup
    echo.
    pause
    goto :end
)

REM Invalid mode
echo Invalid mode: %MODE%
echo Run "todo.bat help" for usage information
pause

:end
exit /b