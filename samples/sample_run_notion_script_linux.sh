#!/bin/bash

# # Set the project directory
# PROJECT_DIR="/home/user/Documents/something/notion"  # Example path to project
# OR, set the project directory dynamically to the script's location
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/notion"  # Path to virtual environment

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to create virtual environment
create_venv() {
    log "Creating fresh virtual environment..."
    if ! python -m venv notion --clear; then
        log "Failed to create virtual environment"
        return 1
    fi
    return 0
}

# Function to setup basic packages
setup_basic_packages() {
    log "Installing basic packages..."
    python -m ensurepip --upgrade
    if ! python -m pip install --upgrade pip setuptools wheel; then
        return 1
    fi

    # Verify pip installation
    if ! command -v pip &> /dev/null; then
        log "Error: pip installation failed"
        return 1
    fi
    return 0
}

# Function to install requirements
install_requirements() {
    if [ -f "requirements.txt" ]; then
        log "Installing requirements from requirements.txt..."
        if ! pip install -r requirements.txt; then
            return 1
        fi
        return 0
    else
        log "Warning: requirements.txt not found!"
        return 1
    fi
}

# Change to project directory or exit if it doesn't exist
cd "$PROJECT_DIR" || {
    log "Error: Project directory $PROJECT_DIR not found"
    exit 1
}

# Try to use existing virtual environment first
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    log "Found existing virtual environment, attempting to use it..."
    source "$VENV_DIR/bin/activate"

    # Try to use existing environment
    if setup_basic_packages && install_requirements; then
        log "Successfully using existing virtual environment"
    else
        log "Issues with existing virtual environment, recreating..."
        deactivate 2>/dev/null || true
        rm -rf "$VENV_DIR"
        if create_venv && \
           source "$VENV_DIR/bin/activate" && \
           setup_basic_packages && \
           install_requirements; then
            log "Successfully created fresh virtual environment"
        else
            log "Error: Failed to setup fresh virtual environment"
            exit 1
        fi
    fi
else
    log "No existing virtual environment found, creating new one..."
    if create_venv && \
       source "$VENV_DIR/bin/activate" && \
       setup_basic_packages && \
       install_requirements; then
        log "Successfully created virtual environment"
    else
        log "Error: Failed to setup virtual environment"
        exit 1
    fi
fi

# Run application
log "Starting application..."
python app.py
