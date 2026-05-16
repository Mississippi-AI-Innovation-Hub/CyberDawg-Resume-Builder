#!/bin/bash
# deploy.sh — Quick setup and launch for WIN Job Center Resume Assistant

set -e

echo "=== WIN Job Center Resume Assistant ==="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Install Python 3.10+."
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python: $PY_VERSION"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS credentials not configured."
    echo "Run: aws configure"
    echo "  or: aws sso login --profile <your-profile>"
    exit 1
fi
echo "AWS: credentials OK"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

# Create logs directory
mkdir -p logs

# Launch
echo ""
echo "Starting app..."
echo "Open http://localhost:8501 in your browser"
echo ""
streamlit run app.py
