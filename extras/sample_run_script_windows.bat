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

:: Function to create virtual environment
:create_venv
call :log "Creating fresh virtual environment..."
python -m venv notion --clear
if errorlevel 1 (
    call :log "Failed to create virtual environment"
    exit /b 1
)
exit /b 0

:: Function to setup basic packages
:setup_basic_packages
call :log "Installing basic packages..."
python -m ensurepip --upgrade
if errorlevel 1 exit /b 1
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1

:: Verify pip installation
where pip >nul 2>nul
if errorlevel 1 (
    call :log "Error: pip installation failed"
    exit /b 1
)
exit /b 0

:: Function to install requirements
:install_requirements
if exist "requirements.txt" (
    call :log "Installing requirements from requirements.txt..."
    pip install -r requirements.txt
    if errorlevel 1 (
        call :log "Failed to install requirements"
        exit /b 1
    )
    exit /b 0
) else (
    call :log "Warning: requirements.txt not found!"
    exit /b 1
)

:: Change to project directory or exit if it doesn't exist
cd /d "%PROJECT_DIR%" || (
    call :log "Error: Project directory %PROJECT_DIR% not found"
    exit /b 1
)

:: Try to use existing virtual environment first
if exist "%VENV_DIR%\Scripts\activate.bat" (
    call :log "Found existing virtual environment, attempting to use it..."
    call "%VENV_DIR%\Scripts\activate.bat"
    if errorlevel 1 (
        call :log "Failed to activate existing environment"
        goto :recreate_env
    )

    :: Try to use existing environment
    call :setup_basic_packages
    if errorlevel 1 goto :recreate_env
    
    call :install_requirements
    if errorlevel 1 goto :recreate_env
    
    call :log "Successfully using existing virtual environment"
    goto :run_app

    :recreate_env
    call :log "Issues with existing virtual environment, recreating..."
    deactivate > nul 2>&1
    rmdir /s /q "%VENV_DIR%" > nul 2>&1
    
    call :create_venv
    if errorlevel 1 exit /b 1
    
    call "%VENV_DIR%\Scripts\activate.bat"
    if errorlevel 1 exit /b 1
    
    call :setup_basic_packages
    if errorlevel 1 exit /b 1
    
    call :install_requirements
    if errorlevel 1 exit /b 1
    
    call :log "Successfully created fresh virtual environment"
) else (
    call :log "No existing virtual environment found, creating new one..."
    call :create_venv
    if errorlevel 1 exit /b 1
    
    call "%VENV_DIR%\Scripts\activate.bat"
    if errorlevel 1 exit /b 1
    
    call :setup_basic_packages
    if errorlevel 1 exit /b 1
    
    call :install_requirements
    if errorlevel 1 exit /b 1
    
    call :log "Successfully created virtual environment"
)

:run_app
:: Run application
call :log "Starting application..."
python app.py
if errorlevel 1 (
    call :log "Error: Application failed to start"
    pause
    exit /b 1
)

:: Keep window open if there were any errors
if errorlevel 1 pause

endlocal