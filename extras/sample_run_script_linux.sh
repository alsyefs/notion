#!/bin/bash

# Set the project directory
PROJECT_DIR="/home/user/path/to/project"
VENV_DIR="$PROJECT_DIR/notion"

# Exit on any error
set -e

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Change to project directory or exit if it doesn't exist
cd "$PROJECT_DIR" || {
    log "Error: Project directory $PROJECT_DIR not found"
    exit 1
}

# Always remove existing virtual environment to ensure clean state
if [ -d "$VENV_DIR" ]; then
    log "Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

# Create new virtual environment with system packages
log "Creating fresh virtual environment..."
python -m venv notion --clear
if [ $? -ne 0 ]; then
    log "Failed to create virtual environment"
    exit 1
fi

# Activate the virtual environment
log "Activating virtual environment..."
source notion/bin/activate

# Ensure basic packages are properly installed
log "Installing basic packages..."
python -m ensurepip --upgrade
python -m pip install --upgrade pip setuptools wheel

# Verify pip installation
if ! command -v pip &> /dev/null; then
    log "Error: pip installation failed"
    exit 1
fi

# Install requirements if requirements.txt exists
if [ -f "requirements.txt" ]; then
    log "Installing requirements from requirements.txt..."
    pip install -r requirements.txt || {
        log "Failed to install requirements"
        exit 1
    }
else
    log "Warning: requirements.txt not found!"
    exit 1
fi

# Run application
log "Starting application..."
python app.py
