@echo off

:: Set the project directory (update this path to your Windows path)
set PROJECT_DIR=C:\path\to\your\project
set VENV_DIR=%PROJECT_DIR%\notion

:: Change to project directory or exit if it doesn't exist
cd /d "%PROJECT_DIR%" || exit /b 1

:: Check if virtual environment exists
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Virtual environment not found. Creating new environment...
    python -m venv notion
    if errorlevel 1 (
        echo Failed to create virtual environment
        exit /b 1
    )
    echo Virtual environment created successfully
)

:: Activate the virtual environment
echo Activating virtual environment...
call notion\Scripts\activate.bat

:: Ensure pip is installed and up to date
echo Ensuring pip is up to date...
python -m ensurepip --upgrade
python -m pip install --upgrade pip

:: Install requirements if requirements.txt exists
if exist "requirements.txt" (
    echo Installing requirements from requirements.txt...
    python -m pip install -r requirements.txt
) else (
    echo Warning: requirements.txt not found!
    exit /b 1
)

:: Run application
python app.py

pause