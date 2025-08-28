# Git Setup Guide for FBR E-Invoicing Project

## 🚀 Quick Git Setup

### Step 1: Initialize Git Repository
```bash
cd your-project-folder
git init
```

### Step 2: Add .gitignore
Copy one of the .gitignore files to your project root:
- **Comprehensive**: Use the detailed version (recommended)
- **Simple**: Use the essential-only version

### Step 3: Create Initial Commit
```bash
# Add all files (respecting .gitignore)
git add .

# Check what will be committed
git status

# Create first commit
git commit -m "Initial commit: FBR E-Invoicing Desktop App

- Setup PyQt6 desktop application
- Configure Neon PostgreSQL database
- Add FBR payload generation logic
- Create professional GUI interface
- Add queue management system"
```

### Step 4: Connect to Remote Repository (Optional)

#### Option A: GitHub
```bash
# Create repo on github.com first, then:
git branch -M main
git remote add origin https://github.com/yourusername/fbr-invoicing.git
git push -u origin main
```

#### Option B: GitLab
```bash
git remote add origin https://gitlab.com/yourusername/fbr-invoicing.git
git push -u origin main
```

## 📋 Recommended Commit Message Format

Use clear, descriptive commit messages:

```bash
git commit -m "feat: add invoice creation dialog

- Create new invoice dialog with customer selection
- Add validation for required FBR fields
- Implement HS code lookup functionality"

git commit -m "fix: resolve database connection timeout

- Increase connection timeout to 30 seconds
- Add retry logic for failed connections  
- Improve error messages for users"

git commit -m "docs: update installation guide

- Add Windows setup instructions
- Include troubleshooting section
- Update dependency requirements"
```

## 🔧 Useful Git Commands for Your Project

### Daily Development
```bash
# Check status
git status

# Add specific files
git add main.py gui/main_window.py

# Add all changes
git add .

# Commit changes
git commit -m "your message"

# Push to remote
git push
```

### Managing Features
```bash
# Create feature branch
git checkout -b feature/invoice-validation

# Switch between branches
git checkout main
git checkout feature/invoice-validation

# Merge feature when done
git checkout main
git merge feature/invoice-validation
```

### Handling Sensitive Files
```bash
# If you accidentally committed sensitive files:
git rm --cached config/app_config.ini
git commit -m "Remove sensitive config file"

# Then add the file to .gitignore
echo "config/app_config.ini" >> .gitignore
git add .gitignore
git commit -m "Add config file to gitignore"
```

## 📁 Recommended Branch Structure

```
main                    # Production-ready code
├── develop            # Development branch
├── feature/gui-redesign    # New features  
├── feature/fbr-validation  # FBR improvements
├── hotfix/database-fix     # Quick fixes
└── release/v1.0           # Release preparation
```

## 🔒 Security Best Practices

### Never Commit These Files:
```bash
# Add these patterns to .gitignore
config/production_config.ini
*.key
*.pem
.env
secrets.json
api_credentials.txt
customer_data/
```

### Example .env File (Not Committed):
```bash
# .env (add to .gitignore!)
DATABASE_PASSWORD=your_secret_password
FBR_API_TOKEN=your_api_token
ENCRYPTION_KEY=your_encryption_key
```

### Example Config Template (Safe to Commit):
```ini
# config/example_config.ini (this CAN be committed)
[DATABASE]
url = postgresql://username:PASSWORD_HERE@host/database

[FBR_API]
endpoint = https://api.fbr.gov.pk/einvoicing
authorization_token = YOUR_TOKEN_HERE
login_id = YOUR_LOGIN_HERE

[APPLICATION]
debug_mode = false
```

## 📈 Release Workflow

### Creating Releases
```bash
# Create release branch
git checkout -b release/v1.0.0

# Update version numbers in files
# Test thoroughly
# Fix any issues

# Merge to main
git checkout main
git merge release/v1.0.0

# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0: FBR E-Invoicing Desktop App

Features:
- Invoice management with FBR compliance
- Queue system for failed submissions
- Professional Windows GUI
- Neon PostgreSQL integration"

# Push everything
git push origin main --tags
```

### Building Distribution
```bash
# Build executable for release
pyinstaller --onefile --windowed --name="FBR_Invoicing_v1.0.0" main.py

# Create release package
mkdir release_package
copy dist\FBR_Invoicing_v1.0.0.exe release_package\
copy README.md release_package\
copy "User Manual.pdf" release_package\
```

## 🤝 Collaboration Tips

### Working with Team
```bash
# Always pull before starting work
git pull

# Create feature branches for new work
git checkout -b feature/your-feature-name

# Regular commits with clear messages
git commit -m "feat: add customer validation logic"

# Push feature branch
git push origin feature/your-feature-name

# Create pull request on GitHub/GitLab
# Get code review before merging
```

### Code Review Checklist
- [ ] No sensitive data in commits
- [ ] .gitignore working properly  
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Clear commit messages

## 🎯 Your Next Steps

1. **Choose a .gitignore** (comprehensive recommended)
2. **Initialize git** in your project folder
3. **Create first commit** with your working code
4. **Set up remote repository** (GitHub/GitLab)
5. **Start using branches** for new features

This sets up proper version control for your FBR E-Invoicing project! 🚀