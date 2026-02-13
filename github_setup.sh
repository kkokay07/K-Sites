#!/bin/bash
# GitHub Repository Setup Script for K-Sites
# Run this after manually creating the repository on GitHub

echo "=========================================="
echo "GitHub Repository Setup for K-Sites"
echo "=========================================="
echo ""

# Check if origin remote exists
if git remote get-url origin &>/dev/null; then
    echo "Updating existing remote 'origin'..."
    git remote set-url origin "https://github.com/kkokay07/k-sites.git"
else
    echo "Adding remote 'origin'..."
    git remote add origin "https://github.com/kkokay07/k-sites.git"
fi

echo ""
echo "Pushing code to GitHub..."
git push -u origin master

echo ""
echo "=========================================="
echo "✓ Code pushed successfully!"
echo "=========================================="
echo ""
echo "Repository: https://github.com/kkokay07/k-sites"
echo "PyPI: https://pypi.org/project/k-sites/"
