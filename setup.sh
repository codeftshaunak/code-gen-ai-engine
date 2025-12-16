#!/bin/bash

# Builder AI Engine - Setup Script
# This script sets up the Python AI Engine environment

set -e

echo "🚀 Builder AI Engine - Setup Script"
echo "===================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.10 or higher is required. Found: $python_version"
    exit 1
fi
echo "✅ Python version: $python_version"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️  Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✅ pip upgraded"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Setup environment file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file and add your API keys:"
    echo "   - E2B_API_KEY or VERCEL_TOKEN (for sandbox)"
    echo "   - ANTHROPIC_API_KEY, OPENAI_API_KEY, etc. (for AI models)"
    echo ""
else
    echo "ℹ️  .env file already exists"
    echo ""
fi

# Success message
echo "✅ Setup complete!"
echo ""
echo "📚 Next steps:"
echo "   1. Edit .env file with your API keys"
echo "   2. Activate virtual environment: source venv/bin/activate"
echo "   3. Run the server: python main.py"
echo "   4. Access docs: http://localhost:3100/api/docs"
echo ""
echo "🎉 Happy coding!"
