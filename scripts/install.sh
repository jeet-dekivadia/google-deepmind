#!/bin/bash

# HALO Installation Script
# Hierarchical Abstraction for Longform Optimization

set -e

echo "🚀 HALO Installation Script"
echo "=========================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.10 or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "✅ Virtual environment created and activated"

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install in development mode
echo ""
echo "🔧 Installing HALO in development mode..."
pip install -e .

echo ""
echo "✅ HALO installation completed successfully!"
echo ""

# Check for API keys
echo "🔐 API Key Configuration"
echo "======================="
echo ""

if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  GEMINI_API_KEY not found in environment variables"
    echo "   To set it up, run:"
    echo "   export GEMINI_API_KEY='your_api_key_here'"
    echo ""
else
    echo "✅ GEMINI_API_KEY found in environment"
fi

if [ -z "$HF_TOKEN" ]; then
    echo "⚠️  HF_TOKEN not found in environment variables"
    echo "   To set it up, run:"
    echo "   export HF_TOKEN='your_huggingface_token_here'"
    echo ""
else
    echo "✅ HF_TOKEN found in environment"
fi

echo ""
echo "🎯 Next Steps:"
echo "=============="
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Set up your API keys (see README.md for instructions)"
echo ""
echo "3. Run the demo:"
echo "   python demo.py"
echo ""
echo "4. Or start the Jupyter notebook:"
echo "   jupyter notebook demo.ipynb"
echo ""
echo "5. Use the CLI:"
echo "   halo --help"
echo ""
echo "📚 For more information, see README.md"
echo ""
echo "🎉 Happy video processing with HALO!" 