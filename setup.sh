#!/bin/bash
# Claude Trader Setup
# One-click setup for voice trading

set -e

echo "==================================="
echo "  Claude Trader Setup"
echo "==================================="

# Check Python
if ! command -v python3.12 &> /dev/null; then
    echo "Python 3.12 required. Install with: brew install python@3.12"
    exit 1
fi

# Create venv
echo "Creating virtual environment..."
python3.12 -m venv .venv
source .venv/bin/activate

# Install deps
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check for whisper
echo ""
echo "Checking speech recognition..."
if python -c "import whisper" 2>/dev/null; then
    echo "✓ Whisper available"
else
    echo "Installing whisper for speech recognition..."
    pip install -q openai-whisper
fi

# Check for sounddevice
if python -c "import sounddevice" 2>/dev/null; then
    echo "✓ Audio recording available"
else
    echo "Installing sounddevice for microphone..."
    pip install -q sounddevice
fi

# Run credential wizard
echo ""
echo "==================================="
echo "  Credential Setup"
echo "==================================="
python setup_wizard.py

echo ""
echo "==================================="
echo "  Setup Complete!"
echo "==================================="
echo ""
echo "To start trading:"
echo "  source .venv/bin/activate"
echo "  python interactive.py        # Text mode"
echo "  python voice/voice_trader.py # Voice mode"
echo ""
