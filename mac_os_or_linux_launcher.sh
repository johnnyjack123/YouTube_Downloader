#!/bin/bash
set -e

cd "$(dirname "$0")"

# ================================
# Check if Python is installed
# ================================
if ! command -v python3 &> /dev/null
then
    echo "Python not found. Installing..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt update && sudo apt install -y python3 python3-venv python3-pip
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install python
    fi
else
    echo "Python is already installed."
fi

# ================================
# Check if ffmpeg is installed
# ================================
if ! command -v ffmpeg &> /dev/null
then
    echo "ffmpeg not found. Installing..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt update && sudo apt install -y ffmpeg
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ffmpeg
    fi
else
    echo "ffmpeg is already installed."
fi

# ================================
# Virtual environment setup
# ================================
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r ./program_files/requirements.txt
else
    echo "Activate virtual environment..."
    source venv/bin/activate
fi

# ================================
# Run the main program
# ================================
python launcher.py
