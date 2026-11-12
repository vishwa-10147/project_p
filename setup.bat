@echo off
REM EmpowerHer: one-command setup and run (Windows).
REM
REM   setup.bat             set up everything and start the app
REM   setup.bat --test      also run the automated tests before starting
REM   setup.bat --no-run    set up only, do not start the server
REM   setup.bat --no-demo   do not create the demo account
REM   set PORT=8080 then setup.bat   use another port (default 8000)
REM
REM Safe to run again: existing keys, data and packages are kept.

setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
set "BACKEND=%ROOT%empowerher\backend"
set "VENV=%ROOT%.venv"
if "%PORT%"=="" set "PORT=8000"
set RUN=1
set TEST=0
set DEMO=1
for %%A in (%*) do (
    if "%%~A"=="--no-run" set RUN=0
    if "%%~A"=="--test" set TEST=1
    if "%%~A"=="--no-demo" set DEMO=0
)

echo.
echo ==^> 1/7 Finding Python 3.11 - 3.13
set "PYTHON="
for %%V in (3.12 3.13 3.11) do (
    if not defined PYTHON (
        py -%%V -c "import sys" >nul 2>&1 && set "PYTHON=py -%%V"
    )
)
if not defined PYTHON (
    python -c "import sys; sys.exit(not (3, 11) <= sys.version_info[:2] <= (3, 13))" >nul 2>&1 && set "PYTHON=python"
)
if not defined PYTHON (
    echo Python 3.11, 3.12 or 3.13 is required. Install it from https://www.python.org/downloads/
    exit /b 1
)
echo Using !PYTHON!

echo.
echo ==^> 2/7 Creating the virtual environment (.venv)
if not exist "%VENV%\Scripts\python.exe" (
    !PYTHON! -m venv "%VENV%" || exit /b 1
) else (
    echo Already exists.
)
set "PY=%VENV%\Scripts\python.exe"

echo.
echo ==^> 3/7 Installing packages (first run takes a few minutes)
"%PY%" -m pip install --quiet --upgrade pip || exit /b 1
"%PY%" -m pip install --quiet -r "%BACKEND%\requirements.txt" || exit /b 1
echo Packages installed.

echo.
echo ==^> 4/7 Creating backend\.env with new encryption keys
cd /d "%BACKEND%"
if exist .env (
    echo .env already exists; keeping your keys.
) else (
    "%PY%" -c "import secrets; from cryptography.fernet import Fernet as F; k=lambda: F.generate_key().decode(); open('.env','w').write('DJANGO_SECRET_KEY='+secrets.token_urlsafe(50)+'\nDJANGO_DEBUG=True\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\nIDEA_VAULT_ENCRYPTION_KEY='+k()+'\nDOCUMENT_ENCRYPTION_KEY='+k()+'\nOPENAI_API_KEY=\nOPENAI_MODEL=gpt-4.1-mini\n')" || exit /b 1
    echo Created .env. Back it up: without these keys encrypted data cannot be read.
)

echo.
echo ==^> 5/7 Preparing datasets and database
if not exist datasets\processed\districts.csv (
    "%PY%" datasets\build_datasets.py || exit /b 1
) else (
    echo Processed datasets present.
)
"%PY%" manage.py migrate --noinput -v 0 || exit /b 1
echo Database ready.

echo.
echo ==^> 6/7 Demo account and tests
if "%DEMO%"=="1" "%PY%" manage.py seed_demo | findstr /v "witness"
if "%TEST%"=="1" (
    "%PY%" manage.py test || exit /b 1
)

if "%RUN%"=="0" (
    echo.
    echo Setup complete. Start the app with: setup.bat
    exit /b 0
)

echo.
echo ==^> 7/7 Starting EmpowerHer at http://localhost:%PORT% (Ctrl+C to stop)
REM Open the browser after the server has had a few seconds to start.
start "" /b cmd /c "timeout /t 4 /nobreak >nul & start http://localhost:%PORT%/"
"%PY%" manage.py runserver 127.0.0.1:%PORT%
