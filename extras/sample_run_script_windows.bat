@echo off
setlocal EnableDelayedExpansion

:: Set the project directory (update this path to your Windows path)
set PROJECT_DIR=C:\path\to\your\project
set VENV_DIR=%PROJECT_DIR%\notion

:: Function to log messages with timestamps (using a label as a function)
:log
set "msg=%~1"
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set "log_time=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%:%datetime:~12,2%"
echo %log_time% - %msg%
goto :eof

:: Change to project directory or exit if it doesn't exist
cd /d "%PROJECT_DIR%" || (
    call :log "Error: Project directory %PROJECT_DIR% not found"
    exit /b 1
)

:: Always remove existing virtual environment to ensure clean state
if exist "%VENV_DIR%" (
    call :log "Removing existing virtual environment..."
    rmdir /s /q "%VENV_DIR%"
    if errorlevel 1 (
        call :log "Error: Failed to remove existing virtual environment"
        exit /b 1
    )
)

:: Create new virtual environment
call :log "Creating fresh virtual environment..."
python -m venv notion --clear
if errorlevel 1 (
    call :log "Error: Failed to create virtual environment"
    exit /b 1
)

:: Activate the virtual environment
call :log "Activating virtual environment..."
call notion\Scripts\activate.bat
if errorlevel 1 (
    call :log "Error: Failed to activate virtual environment"
    exit /b 1
)

:: Ensure basic packages are properly installed
call :log "Installing basic packages..."
python -m ensurepip --upgrade
if errorlevel 1 (
    call :log "Error: Failed to upgrade ensurepip"
    exit /b 1
)

python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    call :log "Error: Failed to upgrade pip, setuptools, and wheel"
    exit /b 1
)

:: Verify pip installation
where pip >nul 2>nul
if errorlevel 1 (
    call :log "Error: pip installation failed"
    exit /b 1
)

:: Install requirements if requirements.txt exists
if exist "requirements.txt" (
    call :log "Installing requirements from requirements.txt..."
    pip install -r requirements.txt
    if errorlevel 1 (
        call :log "Error: Failed to install requirements"
        exit /b 1
    )
) else (
    call :log "Warning: requirements.txt not found!"
    exit /b 1
)

:: Run application
call :log "Starting application..."
python app.py
if errorlevel 1 (
    call :log "Error: Application failed to start"
    exit /b 1
)

:: Keep window open to see any error messages
pause

endlocal