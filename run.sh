#!/bin/bash
# Quick start script for Simple Image Sorter

set -e

echo "Simple Image Sorter - Quick Start"
echo "====================================="
echo ""

PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "Python not found. Please install Python 3.13.x."
    exit 1
fi

python_version=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

USE_UV=false
if command -v uv >/dev/null 2>&1; then
    USE_UV=true
fi

PIP_CMD=""
if command -v pip >/dev/null 2>&1; then
    PIP_CMD="pip"
elif command -v pip3 >/dev/null 2>&1; then
    PIP_CMD="pip3"
elif $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
    PIP_CMD="$PYTHON_CMD -m pip"
fi

echo ""
echo "Choose how to run the app:"
echo "1. Web app (Streamlit)"
echo "2. Desktop app (PyQt6)"
echo ""
read -p "Enter your choice (1 or 2): " choice

case $choice in
    1)
        echo ""
        echo "Installing web app dependencies..."

        if [ "$USE_UV" = true ]; then
            uv sync
            echo ""
            echo "Starting web app..."
            echo "The app will open in your browser at http://localhost:8501"
            uv run python -m streamlit run app/streamlit_app.py
        else
            if [ -z "$PIP_CMD" ]; then
                echo "pip not found. Install pip/pip3 or install uv."
                exit 1
            fi
            eval "$PIP_CMD install -e ."

            echo ""
            echo "Starting web app..."
            echo "The app will open in your browser at http://localhost:8501"
            $PYTHON_CMD -m streamlit run app/streamlit_app.py
        fi
        ;;
    2)
        echo ""
        echo "Installing desktop dependencies..."

        if [ "$USE_UV" = true ]; then
            uv sync --extra desktop
            echo ""
            echo "Starting desktop app..."
            uv run pyqt_main.py
        else
            if [ -z "$PIP_CMD" ]; then
                echo "pip not found. Install pip/pip3 or install uv."
                exit 1
            fi
            eval "$PIP_CMD install -e '.[desktop]'"

            echo ""
            echo "Starting desktop app..."
            $PYTHON_CMD pyqt_main.py
        fi
        ;;
    *)
        echo "Invalid choice. Please enter 1 or 2."
        exit 1
        ;;
esac
