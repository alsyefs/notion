#!/bin/bash

# Set the project directory
PROJECT_DIR="/home/username/path/to/project"
VENV_DIR="$PROJECT_DIR/notion"

# Change to project directory or exit if it doesn't exist
cd "$PROJECT_DIR" || exit 1

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "Virtual environment not found. Creating new environment..."
    python -m venv notion
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment"
        exit 1
    fi
    echo "Virtual environment created successfully"
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source notion/bin/activate

# Ensure pip is installed and up to date
echo "Ensuring pip is up to date..."
python -m ensurepip --upgrade
python -m pip install --upgrade pip

# Install requirements if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing requirements from requirements.txt..."
    python -m pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found!"
    exit 1
fi

# Run application
python app.py
