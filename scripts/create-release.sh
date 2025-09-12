#!/bin/bash

# Simple release creation script for YNAB Amazon Categorizer
# Usage: ./create-release.sh v1.0.0

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 v1.0.0"
    exit 1
fi

echo "🎯 Creating release $VERSION"

# Validate we're in a git repo
if [ ! -d ".git" ]; then
    echo "❌ Not in a git repository"
    exit 1
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  You have uncommitted changes:"
    git status --short
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create and push tag
echo "🏷️  Creating tag $VERSION"
git tag "$VERSION"

echo "📤 Pushing tag to origin"
git push origin "$VERSION"

echo "✅ Release tag created and pushed!"
echo "🔄 GitHub Action will now create the release automatically"
echo "   Monitor progress at: https://github.com/YOUR_USERNAME/ynab-amazon-categorizer/actions"