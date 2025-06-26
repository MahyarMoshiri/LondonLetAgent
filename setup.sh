#!/bin/bash
# Enhanced Property Canvassing Agent - Setup Script

echo "🏠 Enhanced Property Canvassing Agent - Setup"
echo "=============================================="
echo

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1)
if [[ $? -eq 0 ]]; then
    echo "✅ $python_version"
else
    echo "❌ Python 3 not found. Please install Python 3.8+ first."
    exit 1
fi

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected. Recommended to use one:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate  # Linux/Mac"
    echo "   venv\\Scripts\\activate     # Windows"
    echo
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt
if [[ $? -eq 0 ]]; then
    echo "✅ Python dependencies installed"
else
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium
if [[ $? -eq 0 ]]; then
    echo "✅ Playwright browsers installed"
else
    echo "❌ Failed to install Playwright browsers"
    exit 1
fi

# Create data directory
echo "📁 Creating data directory..."
mkdir -p data
mkdir -p logs
echo "✅ Directories created"

# Test installation
echo "🧪 Testing installation..."
python3 -c "
import sys
sys.path.insert(0, 'src')
try:
    from src.scraping_module.gumtree_scraper import GumtreeScraper
    from src.ai_module import AIModule
    from src.models import UserCriteria
    print('✅ All modules imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

if [[ $? -eq 0 ]]; then
    echo "✅ Installation test passed"
else
    echo "❌ Installation test failed"
    exit 1
fi

echo
echo "🎉 Setup completed successfully!"
echo
echo "📚 Next steps:"
echo "1. Run quick test:     python3 quick_test.py"
echo "2. Run full search:    python3 -m src.input_module --location 'North West London' --max_price 2000 --private_only"
echo "3. Check results:      ls data/"
echo "4. Read docs:          cat docs/SETUP.md"
echo
echo "🔗 Documentation:"
echo "   Setup Guide:        docs/SETUP.md"
echo "   Troubleshooting:    docs/TROUBLESHOOTING.md"
echo "   Changelog:          docs/CHANGELOG.md"
echo
echo "🚀 Ready to find 500+ properties instead of 25!"

