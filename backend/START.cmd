@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
pushd "%~dp0"
if errorlevel 1 goto directory_error

if not exist "start.py" goto missing_files
if not exist "app\config.py" goto missing_files

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 goto use_venv
    echo [WARNING] Existing .venv could not run a compatible Python.
)

py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if not errorlevel 1 goto use_py

python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if not errorlevel 1 goto use_python

echo [ERROR] No working Python 3.11 or newer was found.
echo Check Python installation and PATH. Run py -0p in PowerShell.
echo Do not disable Windows security or run this as administrator to bypass an error.
set "RC=1"
goto finish

:use_venv
".venv\Scripts\python.exe" -u "start.py" %*
set "RC=%errorlevel%"
goto finish

:use_py
py -3 -u "start.py" %*
set "RC=%errorlevel%"
goto finish

:use_python
python -u "start.py" %*
set "RC=%errorlevel%"
goto finish

:missing_files
echo [ERROR] Extract the COMPLETE backend folder first.
echo START.cmd, start.py and app must be inside the same backend folder.
set "RC=1"
goto finish

:directory_error
echo [ERROR] Cannot open the backend folder.
pause
endlocal & exit /b 1

:finish
echo.
echo Launcher exit code: %RC%
if not "%RC%"=="0" (
    echo Startup did not complete. Copy the ERROR above before closing this window.
    echo Redact passwords, tokens and connection strings before sharing logs.
    pause
)
popd
endlocal & exit /b %RC%
