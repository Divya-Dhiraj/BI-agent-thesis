# Git Repository Setup Guide

## Step 1: Change Git Account Credentials

Run these commands with your new account information:

```bash
git config --global user.name "YourNewUsername"
git config --global user.email "yournewemail@example.com"
```

To verify the changes:
```bash
git config --global user.name
git config --global user.email
```

## Step 2: Create a New Repository

1. Go to GitHub (https://github.com), GitLab, or Bitbucket
2. Click "New repository" or "+" button
3. Choose a repository name (e.g., `BI-agent-thesis`)
4. **DO NOT** initialize with README, .gitignore, or license (since we already have files)
5. Click "Create repository"
6. Copy the repository URL (it will look like: `https://github.com/username/repo-name.git`)

## Step 3: Commit Your Files

Files are already staged. Now commit them:

```bash
git commit -m "Initial commit"
```

## Step 4: Add Remote and Push

Replace `<your-repo-url>` with the URL you copied in Step 2:

```bash
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

## Alternative: If you need to authenticate

If you're using GitHub, you may need to use a Personal Access Token instead of password:
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate a new token with `repo` permissions
3. Use the token as your password when pushing

## Troubleshooting

If you get authentication errors:
- For GitHub: Use a Personal Access Token
- For GitLab: Use a Personal Access Token or SSH key
- For Bitbucket: Use an App Password

If you need to change the remote URL later:
```bash
git remote set-url origin <new-repo-url>
```
