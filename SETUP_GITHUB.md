# Setting Up GitHub Repository for Giggles

Follow these steps to push your code to GitHub.

## Prerequisites

- Git installed on your machine
- GitHub account created

## Step-by-Step Instructions

### 1. Check Current Git Status

First, check if you already have a git repository initialized:

```bash
cd /Users/neilsethi/git/giggles-cli
git status
```

If you see "not a git repository", proceed to step 2. Otherwise, skip to step 3.

### 2. Initialize Git Repository

```bash
git init
```

### 3. Add All Files to Git

```bash
# Add all files (excluding .gitignore entries)
git add .

# Check what will be committed
git status
```

### 4. Make Initial Commit

```bash
git commit -m "Initial commit: Giggles - AI-powered laughter tracker

- Complete FastAPI backend with Supabase authentication
- YAMNet AI integration for laughter detection
- Limitless API integration for audio retrieval
- Mobile-responsive frontend
- Encrypted API key storage
- Row Level Security (RLS) implementation
- Audio processing and storage pipeline
- Daily laughter tracking dashboard"
```

### 5. Create GitHub Repository

#### Option A: Using GitHub Website

1. Go to https://github.com/new
2. Repository name: `giggles-cli` (or your preferred name)
3. Description: "🎭 AI-powered laughter tracker using YAMNet and Limitless AI"
4. Choose **Public** or **Private**
5. **DO NOT** initialize with README, .gitignore, or license (you already have these)
6. Click "Create repository"

#### Option B: Using GitHub CLI (if installed)

```bash
gh repo create giggles-cli --public --description "🎭 AI-powered laughter tracker using YAMNet and Limitless AI"
```

### 6. Add Remote Origin

Copy the repository URL from GitHub (e.g., `https://github.com/yourusername/giggles-cli.git`), then:

```bash
git remote add origin https://github.com/yourusername/giggles-cli.git
```

Replace `yourusername` with your actual GitHub username.

### 7. Set Main Branch (if needed)

```bash
git branch -M main
```

### 8. Push to GitHub

```bash
# Push to GitHub
git push -u origin main
```

If prompted, enter your GitHub username and a Personal Access Token (not password).

### 9. Verify on GitHub

Visit your repository on GitHub to confirm all files are uploaded:
```
https://github.com/yourusername/giggles-cli
```

## Important Notes

### Security Checklist

Before pushing, verify these files are **NOT** in your repository:

- ✅ `.env` files (already in .gitignore)
- ✅ Audio files (`.wav`, `.ogg`, `.mp3` - already in .gitignore)
- ✅ Log files (`.log` - already in .gitignore)
- ✅ Database files (`.db`, `.sqlite` - already in .gitignore)
- ✅ Virtual environment (`venv/` - already in .gitignore)
- ✅ Model files (`.h5`, `.pb` - already in .gitignore)

You can verify with:
```bash
git status
```

### What NOT to Push

The `.gitignore` file ensures these are NOT committed:
- Environment variables (`.env`)
- User data (audio files, logs)
- Virtual environment
- Secrets and credentials

### First-Time Pushing Tips

1. **Create a .env.example**: Create a template file showing required environment variables (without actual secrets)
2. **Update README.md**: Make sure the README doesn't contain any actual secrets or API keys
3. **Clean up test data**: Remove any test files or temporary scripts
4. **Review commit history**: You can review what's being committed with `git diff --cached`

## Common Issues

### Issue: "Updates were rejected"

```bash
# Pull remote changes first
git pull origin main --rebase

# Then push
git push -u origin main
```

### Issue: "Authentication failed"

You need a Personal Access Token (PAT):

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope
3. Use the token as your password when pushing

### Issue: Large files

If you see warnings about large files:

```bash
# Check large files
git ls-files | xargs ls -lh | sort -k5 -hr | head -20

# Remove accidentally committed large files
git rm --cached path/to/large-file

# Add to .gitignore and commit
git add .gitignore
git commit -m "Remove large files and update gitignore"
```

## Next Steps

After successfully pushing to GitHub:

1. ✅ Add repository description on GitHub
2. ✅ Add topics/tags (e.g., `python`, `fastapi`, `ai`, `laughter-detection`)
3. ✅ Set up GitHub Pages (if you want documentation site)
4. ✅ Configure branch protection rules
5. ✅ Add CONTRIBUTING.md for contributors
6. ✅ Consider adding CI/CD with GitHub Actions

## Future Updates

To push future changes:

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "Description of your changes"

# Push to GitHub
git push
```
