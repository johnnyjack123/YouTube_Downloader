@echo off
cd /d "%~dp0"

:: ================================
:: Check if Python is installed
:: ================================
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python not found. Installing via winget...
    winget install -e --id Python.Python.3.13.5
) else (
    echo Python is already installed.
)

:: ================================
:: Check if ffmpeg is installed
:: ================================
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo ffmpeg not found. Installing via winget...
    winget install -e --id Gyan.FFmpeg
) else (
    echo ffmpeg is already installed.
)

:: ================================
:: Virtual environment setup
:: ================================
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv

    echo Activate virtual environment...
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    call pip install -r ./program_files/requirements.txt
) else (
    echo Activate virtual environment...
    call venv\Scripts\activate.bat
)

:: ================================
:: Run the main program
:: ================================
call python launcher.py

:: Keep CMD open
cmd
