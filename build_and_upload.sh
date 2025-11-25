#!/bin/bash
# Build and upload script for claude-code-viewer

set -e

echo "🔨 Building Claude Code Viewer package..."

# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Install build dependencies
pip install --upgrade pip build twine

# Build the package
echo "📦 Building package..."
python -m build

# Check the package
echo "🔍 Checking package..."
twine check dist/*

echo "✅ Package built successfully!"
echo "📊 Package contents:"
ls -la dist/

echo ""
echo "🚀 To upload to PyPI:"
echo "   Test PyPI: twine upload --repository testpypi dist/*"
echo "   Real PyPI: twine upload dist/*"
echo ""
echo "🔑 Make sure you have set up your PyPI token:"
echo "   pip install keyring"
echo "   keyring set https://upload.pypi.org/legacy/ __token__"