#!/bin/bash
# run.sh - Start Jupyter notebook for LLVM IR Generator

set -e

echo "=========================================="
echo "▶️  LLVM IR Generator - Run Script"
echo "=========================================="

# Check if Groq API key is set
if [ -z "$GROQ_API_KEY" ]; then
    echo ""
    echo "⚠️  GROQ_API_KEY environment variable not set!"
    echo ""
    echo "Please set it before running:"
    echo "  export GROQ_API_KEY='gsk_...'"
    echo ""
    read -p "Enter your Groq API Key now (or press Ctrl+C to exit): " api_key
    if [ -n "$api_key" ]; then
        export GROQ_API_KEY="$api_key"
        echo "✅ API key set."
    fi
    echo ""
fi

# Check if Jupyter is installed
if ! command -v jupyter &> /dev/null; then
    echo "❌ Jupyter not installed. Installing..."
    pip install jupyter
fi

# Find the notebook
NOTEBOOK_NAME="LLVm_IR_Generator_v2.ipynb"
if [ ! -f "$NOTEBOOK_NAME" ]; then
    echo "❌ Error: $NOTEBOOK_NAME not found in current directory."
    echo "Please run this script from the project root directory."
    exit 1
fi

echo ""
echo "Starting Jupyter Notebook..."
echo "=========================================="
echo ""
echo "📓 Access the notebook at: http://localhost:8888"
echo ""
echo "Instructions:"
echo "  1. Run cells in order (1 → 2 → 3 → 4)"
echo "  2. Cell 1: Installs dependencies"
echo "  3. Cell 2: Set Groq API key"
echo "  4. Cell 3: Core logic loads"
echo "  5. Cell 4: Interactive UI"
echo "  6. Cell 5 (optional): Batch testing"
echo ""
echo "Press Ctrl+C to stop the server."
echo "=========================================="
echo ""

# Start Jupyter
jupyter notebook "$NOTEBOOK_NAME"
