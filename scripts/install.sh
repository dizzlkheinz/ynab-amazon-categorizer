#!/bin/bash

# YNAB Amazon Categorizer - Installation Script for Linux/Mac
# This script downloads and sets up the YNAB Amazon Categorizer

set -e

REPO="dizzlkheinz/ynab-amazon-categorizer"
INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/ynab-amazon-categorizer"

echo "🎯 Installing YNAB Amazon Categorizer..."

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# Detect platform
PLATFORM=""
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
else
    echo "❌ Unsupported platform: $OSTYPE"
    echo "Supported platforms: Linux, macOS"
    exit 1
fi

# Get latest release info
echo "📡 Getting latest release information..."
LATEST_RELEASE=$(curl -s "https://api.github.com/repos/$REPO/releases/latest")
VERSION=$(echo "$LATEST_RELEASE" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

if [ -z "$VERSION" ]; then
    echo "❌ Could not get latest version information"
    exit 1
fi

echo "📦 Latest version: $VERSION"

# Download executable
EXECUTABLE_NAME="ynab-amazon-categorizer-$PLATFORM"
DOWNLOAD_URL="https://github.com/$REPO/releases/download/$VERSION/$EXECUTABLE_NAME"

echo "⬇️  Downloading executable..."
curl -L -o "$INSTALL_DIR/ynab-amazon-categorizer" "$DOWNLOAD_URL"
chmod +x "$INSTALL_DIR/ynab-amazon-categorizer"

# Download .env.example
echo "⬇️  Downloading configuration template..."
curl -L -o "$CONFIG_DIR/.env.example" "https://github.com/$REPO/releases/download/$VERSION/.env.example"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "⚠️  Warning: $HOME/.local/bin is not in your PATH"
    echo "   Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Copy the configuration template:"
echo "   cp \"$CONFIG_DIR/.env.example\" \"$CONFIG_DIR/.env\""
echo ""
echo "2. Edit the configuration file with your YNAB credentials:"
echo "   nano \"$CONFIG_DIR/.env\""
echo ""
echo "3. Run the program:"
echo "   ynab-amazon-categorizer"
echo ""
echo "📚 For setup instructions, visit: https://github.com/$REPO#readme"