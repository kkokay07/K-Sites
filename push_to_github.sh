#!/bin/bash
# Push K-Sites code to GitHub
# This script provides instructions for pushing code

echo "=========================================="
echo "Push K-Sites to GitHub"
echo "=========================================="
echo ""

# Check if we can use the token
if command -v gh &> /dev/null; then
    echo "GitHub CLI found. Attempting to authenticate..."
    echo "$GITHUB_TOKEN" | gh auth login --with-token 2>/dev/null
    
    if gh auth status &>/dev/null; then
        echo "✓ Authenticated with GitHub CLI"
        gh repo clone kkokay07/K-Sites /tmp/k-sites-temp 2>/dev/null || true
        cd /home/iiab/Documents/K-sites
        git remote remove origin 2>/dev/null
        git remote add origin https://github.com/kkokay07/K-Sites.git
        git push -u origin master
        echo "✓ Code pushed successfully!"
        exit 0
    fi
fi

echo "Please push manually using one of these methods:"
echo ""
echo "Method 1: Using Git credential cache (recommended)"
echo "  cd /home/iiab/Documents/K-sites"
echo "  git remote add origin https://github.com/kkokay07/K-Sites.git"
echo "  git push -u origin master"
echo "  # Enter your GitHub username and password (or personal access token)"
echo ""
echo "Method 2: Using SSH (if configured)"
echo "  cd /home/iiab/Documents/K-sites"
echo "  git remote add origin git@github.com:kkokay07/K-Sites.git"
echo "  git push -u origin master"
echo ""
echo "Repository URL: https://github.com/kkokay07/K-Sites"
