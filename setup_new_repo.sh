#!/bin/bash

# Script to change git account and push to new repository
# Usage: ./setup_new_repo.sh

echo "=== Git Account Setup ==="
echo ""
echo "Current git configuration:"
git config --global user.name
git config --global user.email
echo ""
echo "To change your git account, run:"
echo "  git config --global user.name 'YourNewUsername'"
echo "  git config --global user.email 'yournewemail@example.com'"
echo ""
echo "=== Next Steps ==="
echo "1. Create a new repository on GitHub/GitLab/Bitbucket"
echo "2. Copy the repository URL (e.g., https://github.com/username/repo-name.git)"
echo "3. Run these commands:"
echo "   git add ."
echo "   git commit -m 'Initial commit'"
echo "   git remote add origin <your-repo-url>"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
