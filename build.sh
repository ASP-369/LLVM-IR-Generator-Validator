#!/bin/bash
# build.sh - Install dependencies for LLVM IR Generator

set -e

echo "=========================================="
echo "🔧 LLVM IR Generator - Build Script"
echo "=========================================="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    OS="unknown"
fi

echo "[1/4] Detecting system: $OS"

# Install LLVM tools
echo "[2/4] Installing LLVM tools..."

case $OS in
    linux)
        echo "  Using apt-get..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq llvm clang
        ;;
    macos)
        echo "  Using homebrew..."
        brew install llvm
        ;;
    windows)
        echo "  Please install LLVM from: https://releases.llvm.org/"
        echo "  Or use: choco install llvm"
        ;;
    *)
        echo "  Unsupported OS. Please install LLVM manually."
        exit 1
        ;;
esac

# Verify LLVM installation
echo "[3/4] Verifying LLVM installation..."
tools=("clang" "llvm-as" "opt" "lli")
for tool in "${tools[@]}"; do
    if command -v "$tool" &> /dev/null; then
        version=$($tool --version | head -1)
        echo "  ✅ $tool: $version"
    else
        echo "  ❌ $tool: NOT FOUND"
        exit 1
    fi
done

# Install Python dependencies
echo "[4/4] Installing Python packages..."
echo "  Installing groq and ipywidgets..."
pip install -q groq ipywidgets

# Verify Python packages
echo ""
echo "  Verifying Python packages..."
python3 << 'EOF'
try:
    import groq
    print(f"  ✅ groq {groq.__version__}")
except ImportError:
    print("  ❌ groq not found")
    exit(1)

try:
    import ipywidgets
    print(f"  ✅ ipywidgets {ipywidgets.__version__}")
except ImportError:
    print("  ❌ ipywidgets not found")
    exit(1)
EOF

echo ""
echo "=========================================="
echo "✅ Build complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Set your Groq API key:"
echo "     export GROQ_API_KEY='your-key-here'"
echo ""
echo "  2. Run the notebook:"
echo "     jupyter notebook LLVm_IR_Generator_v2.ipynb"
echo ""
