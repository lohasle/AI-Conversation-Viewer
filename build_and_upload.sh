#!/bin/bash
# Build and upload script for claude-code-viewer
# Usage: ./build_and_upload.sh [test|prod|build-only]

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current version from pyproject.toml
VERSION=$(grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

echo -e "${BLUE}🔨 Building Claude Code Viewer package...${NC}"
echo -e "${BLUE}📌 Current version: ${GREEN}${VERSION}${NC}"
echo ""

# Clean previous builds
echo -e "${YELLOW}🧹 Cleaning previous builds...${NC}"
rm -rf build/ dist/ *.egg-info/ claude_viewer.egg-info/

# Install build dependencies
echo -e "${YELLOW}📥 Installing build dependencies...${NC}"
pip install --upgrade pip build twine

# Build the package
echo ""
echo -e "${BLUE}📦 Building package...${NC}"
python -m build

# Check the package
echo ""
echo -e "${BLUE}🔍 Checking package...${NC}"
twine check dist/*

echo ""
echo -e "${GREEN}✅ Package built successfully!${NC}"
echo -e "${BLUE}📊 Package contents:${NC}"
ls -lh dist/

# Determine upload target
UPLOAD_TARGET=""
if [ "$1" == "build-only" ]; then
    echo ""
    echo -e "${GREEN}✅ Build complete. Skipping upload.${NC}"
    exit 0
elif [ "$1" == "test" ]; then
    UPLOAD_TARGET="test"
elif [ "$1" == "prod" ]; then
    UPLOAD_TARGET="prod"
else
    # Interactive mode
    echo ""
    echo -e "${YELLOW}🚀 Upload options:${NC}"
    echo "  1) Test PyPI (recommended for testing)"
    echo "  2) Production PyPI (live release)"
    echo "  3) Skip upload"
    echo ""
    read -p "Select option [1-3]: " choice

    case $choice in
        1)
            UPLOAD_TARGET="test"
            ;;
        2)
            UPLOAD_TARGET="prod"
            ;;
        3)
            echo -e "${GREEN}✅ Build complete. Upload skipped.${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Invalid choice. Exiting.${NC}"
            exit 1
            ;;
    esac
fi

# Upload to selected target
if [ "$UPLOAD_TARGET" == "test" ]; then
    echo ""
    echo -e "${YELLOW}📤 Uploading to Test PyPI...${NC}"
    echo -e "${BLUE}Version: ${VERSION}${NC}"
    echo ""
    read -p "Continue? [y/N]: " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        twine upload --repository testpypi dist/*
        echo ""
        echo -e "${GREEN}✅ Upload to Test PyPI successful!${NC}"
        echo -e "${BLUE}🔗 View at: https://test.pypi.org/project/ai-coder-viewer/${VERSION}/${NC}"
        echo ""
        echo -e "${YELLOW}📥 Test installation:${NC}"
        echo "  pip install --index-url https://test.pypi.org/simple/ ai-coder-viewer==${VERSION}"
    else
        echo -e "${YELLOW}❌ Upload cancelled.${NC}"
        exit 0
    fi

elif [ "$UPLOAD_TARGET" == "prod" ]; then
    echo ""
    echo -e "${RED}⚠️  WARNING: Uploading to PRODUCTION PyPI!${NC}"
    echo -e "${BLUE}Package: ai-coder-viewer${NC}"
    echo -e "${BLUE}Version: ${VERSION}${NC}"
    echo ""
    echo -e "${YELLOW}This will publish version ${VERSION} to PyPI permanently.${NC}"
    echo -e "${YELLOW}Make sure you have:${NC}"
    echo "  1. Updated version number in pyproject.toml"
    echo "  2. Updated CHANGELOG.md"
    echo "  3. Committed all changes"
    echo "  4. Tagged the release: git tag v${VERSION}"
    echo ""
    read -p "Are you absolutely sure? [yes/NO]: " confirm
    if [ "$confirm" == "yes" ]; then
        twine upload dist/*
        echo ""
        echo -e "${GREEN}🎉 Upload to PyPI successful!${NC}"
        echo -e "${BLUE}🔗 View at: https://pypi.org/project/ai-coder-viewer/${VERSION}/${NC}"
        echo ""
        echo -e "${YELLOW}📥 Users can now install with:${NC}"
        echo "  pip install ai-coder-viewer==${VERSION}"
        echo "  pip install --upgrade ai-coder-viewer"
        echo ""
        echo -e "${YELLOW}📝 Next steps:${NC}"
        echo "  1. Create GitHub release: https://github.com/lohasle/AI-Conversation-Viewer/releases/new"
        echo "  2. Tag: v${VERSION}"
        echo "  3. Push tags: git push origin v${VERSION}"
    else
        echo -e "${RED}❌ Upload cancelled.${NC}"
        exit 0
    fi
fi

echo ""
echo -e "${GREEN}✅ All done!${NC}"