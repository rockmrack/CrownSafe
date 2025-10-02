# BabyShield – Contributing Guide

## Overview

This document defines the development workflow for BabyShield backend. Following these rules ensures code quality, stability, and safe deployments.

---

## 0. Golden Rules

**NEVER:**
- Push directly to `main`
- Bypass required CI checks
- Commit secrets, local environments, or build artifacts

**ALWAYS:**
- Work in feature branches
- Create Pull Requests for all changes
- Wait for green CI checks before merging

**Required CI Checks:**
- `Smoke — Account Deletion`
- `Smoke — Barcode Search`
- `Unit — Account Deletion`

---

## 1. Starting a Task

### Branch Naming Convention

Use clear, descriptive branch names with prefixes:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feat/` | New features | `feat/azure-storage-migration` |
| `fix/` | Bug fixes | `fix/token-validation-error` |
| `chore/` | Maintenance, refactoring | `chore/update-dependencies` |
| `docs/` | Documentation only | `docs/deployment-guide` |
| `test/` | Test additions/fixes | `test/account-deletion-unit` |

### Create Your Branch

```bash
# Start from latest main
git checkout main
git pull --rebase origin main

# Create feature branch
git checkout -b feat/your-feature-name
```

---

## 2. Making Changes

### Principles

1. **Explain before changing** - State what you'll change and why
2. **Make small, focused changes** - One logical change per commit
3. **Show diffs** - Review changes before committing
4. **Stay in scope** - Don't modify unrelated files
5. **Test locally** - Verify changes work before pushing

### What NOT to Commit

**Never commit these files/directories:**
```
.venv/
.venv310/
venv/
node_modules/
.env
.env.local
*.pyc
__pycache__/
.cursor/
.idea/
.vscode/settings.json
*.log
td.json
td2.json
```

These are already in `.gitignore` - respect it!

---

## 3. Committing Changes

### Conventional Commits Format

Use structured commit messages following [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `chore:` - Maintenance tasks
- `docs:` - Documentation changes
- `refactor:` - Code restructuring (no functionality change)
- `test:` - Adding/updating tests
- `perf:` - Performance improvements
- `ci:` - CI/CD configuration changes

**Examples:**
```bash
# Good commits
git commit -m "feat: add Azure Blob Storage support"
git commit -m "fix: handle missing token in auth response"
git commit -m "chore: update boto3 to latest version"
git commit -m "docs: add deployment procedures for Azure"

# Bad commits (avoid these)
git commit -m "fixed stuff"
git commit -m "updates"
git commit -m "WIP"
```

### Commit and Push

```bash
# Stage your changes
git add -A  # or specific files: git add file1.py file2.py

# Commit with conventional commit message
git commit -m "feat: implement presigned URL generation for Azure Blob"

# Push to remote
git push -u origin feat/your-feature-name
```

---

## 4. Creating a Pull Request

### PR Title

Use the same format as your commit message:
```
feat: implement Azure Blob Storage integration
fix: correct token validation in auth endpoint
```

### PR Description Template

```markdown
## What Changed
- Replaced AWS S3 SDK (boto3) with Azure Blob Storage SDK
- Updated `core_infra/s3_uploads.py` to use Azure SAS tokens
- Added new environment variables for Azure Storage

## Why
AWS infrastructure is being migrated to Azure. S3 operations need to be replaced with Azure Blob Storage equivalents.

## Testing
- [x] Local testing with Azure Storage Emulator
- [x] Unit tests pass
- [x] Smoke tests pass (account deletion, barcode search)

## Risk Assessment
**Risk Level:** Medium

**Rollback Plan:**
- Revert PR #XXX
- Restore AWS environment variables
- Redeploy previous image: `production-fixed-20251001`

## Verification Steps
1. Verify image upload works: `POST /api/v1/visual/upload`
2. Check presigned URL generation returns valid Azure SAS token
3. Confirm download works via generated URL
```

### Open the PR

1. Go to: https://github.com/BabyShield/babyshield-backend/pulls
2. Click **New Pull Request**
3. Base: `main` ← Compare: `feat/your-feature-name`
4. Fill in title and description
5. Click **Create Pull Request**

---

## 5. CI Checks & Branch Updates

### Required Checks

All three must be GREEN before merge:

1. **Smoke — Account Deletion**
   - Tests: Register → Login → Delete Account → Verify Token Revoked
   - Must pass with live API

2. **Smoke — Barcode Search**
   - Tests: Barcode lookup and search functionality
   - Must return valid results

3. **Unit — Account Deletion**
   - Tests: Unit tests for account deletion logic
   - Must pass with pytest fixtures

### Keeping Branch Updated

If `main` has new commits after you created your branch:

```bash
# Fetch latest changes
git fetch origin

# Rebase your branch on top of main
git rebase origin/main

# If conflicts, resolve them, then:
git add <resolved-files>
git rebase --continue

# Force push (safe because it's your feature branch)
git push --force-with-lease
```

**GitHub UI Alternative:**
- Click **Update branch** button on PR page

---

## 6. Merging

### Pre-Merge Checklist

- [ ] All required CI checks are GREEN
- [ ] Code review approved (if required)
- [ ] PR description is complete
- [ ] No merge conflicts
- [ ] Branch is up to date with `main`

### Merge Method

**Always use: Squash and Merge**

This keeps `main` history clean with one commit per feature/fix.

### After Merge

```bash
# Switch back to main
git checkout main

# Pull the merged changes
git pull --rebase origin main

# Delete your feature branch (local)
git branch -d feat/your-feature-name

# Delete remote branch (GitHub usually does this automatically)
git push origin --delete feat/your-feature-name
```

---

## 7. Secrets & Environment Variables

### CI Secrets (GitHub Actions)

These are configured in GitHub Settings → Secrets:

| Secret | Purpose |
|--------|---------|
| `SMOKE_TEST_EMAIL` | Test account email for smoke tests |
| `SMOKE_TEST_PASSWORD` | Test account password |
| `SLACK_WEBHOOK_URL` | (Optional) Slack notifications |

### Security Rules

**DO:**
- Use environment variables for sensitive data
- Store secrets in GitHub Secrets or AWS Secrets Manager
- Use `.env` files locally (never commit them)

**DON'T:**
- Print secrets to logs
- Echo tokens in CI output
- Commit API keys, passwords, or tokens
- Share secrets via chat or email

---

## 8. What Cursor Must NOT Do

Cursor AI assistant must follow these restrictions:

**NEVER:**
1. Push directly to `main` branch
2. Commit virtualenvs (`.venv`, `venv/`)
3. Commit `.env` files or secrets
4. Commit large binaries or build artifacts
5. Change CI workflow names (breaks required checks)
6. Bypass CI checks
7. Force push to `main`
8. Modify `.gitignore` to allow forbidden files

**ALWAYS:**
1. Create feature branches
2. Use conventional commit messages
3. Explain changes before making them
4. Show diffs for review
5. Run tests before pushing

---

## 9. Useful Commands

### Branch Management

```bash
# List all branches
git branch -a

# Switch to existing branch
git checkout feat/existing-branch

# Delete local branch
git branch -d feat/old-branch

# Delete remote branch
git push origin --delete feat/old-branch
```

### Saving Work in Progress

```bash
# Stash changes (including untracked files)
git stash -u

# List stashes
git stash list

# Apply most recent stash
git stash pop

# Apply specific stash
git stash apply stash@{0}
```

### Sync Without Losing Work

```bash
# Save current work
git stash -u

# Update main
git checkout main
git pull --rebase origin main

# Start new task
git checkout -b fix/new-task

# Or go back to previous branch
git checkout feat/previous-task
git stash pop
```

### Undo Mistakes

```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Discard all local changes
git reset --hard HEAD

# Restore specific file
git checkout -- filename.py

# Abort rebase
git rebase --abort
```

---

## 10. Deployment Process

### Production Deployment

After merging to `main`, deploy to production:

```bash
# Use automated deployment script
.\deploy_prod_digest_pinned.ps1

# Or specify custom tag
.\deploy_prod_digest_pinned.ps1 -Tag "production-fixed-20251002"

# Verify deployment
.\verify_deployment.ps1 -Tag "production-fixed-20251002"
```

### Deployment Checklist

- [ ] All tests pass locally
- [ ] PR merged to `main`
- [ ] Latest `main` pulled locally
- [ ] Build Docker image from `Dockerfile.final`
- [ ] Push to ECR with digest-pinned tag
- [ ] Update ECS task definition
- [ ] Force new deployment
- [ ] Verify via health checks
- [ ] Monitor CloudWatch logs

See `DEPLOYMENT_PROCEDURES.md` for complete deployment guide.

---

## 11. Getting Help

### Resources

- **Deployment Guide:** `DEPLOYMENT_PROCEDURES.md`
- **API Documentation:** https://babyshield.cureviax.ai/docs
- **API Endpoints:** `API_ENDPOINTS_DOCUMENTATION.md`
- **Architecture:** `COMPLETE_SYSTEM_ANALYSIS.md`

### Common Issues

**CI checks failing?**
- Check GitHub Actions logs
- Verify secrets are set correctly
- Ensure tests pass locally: `pytest tests/`

**Merge conflicts?**
- Fetch latest: `git fetch origin`
- Rebase: `git rebase origin/main`
- Resolve conflicts in editor
- Continue: `git rebase --continue`

**Branch out of date?**
- Update: `git pull --rebase origin main`
- Force push: `git push --force-with-lease`

---

## 12. Why This Workflow?

### Benefits

**Feature Branches:**
- Isolate changes
- Enable parallel development
- Easy to abandon/rollback

**Pull Requests:**
- Code review opportunity
- Discussion platform
- Documentation of changes

**Required CI Checks:**
- Catch bugs before production
- Ensure API stability
- Verify critical user flows

**Conventional Commits:**
- Clear change history
- Easy to generate changelogs
- Semantic versioning support

**Squash Merging:**
- Clean `main` history
- One commit per feature
- Easy to revert

---

## 13. Examples

### Example: Feature Development Flow

```bash
# Day 1: Start feature
git checkout main
git pull --rebase origin main
git checkout -b feat/azure-blob-storage

# Make changes
# Edit core_infra/s3_uploads.py
# Add Azure SDK code

git add core_infra/s3_uploads.py
git commit -m "feat: add Azure Blob Storage presigned URL generation"
git push -u origin feat/azure-blob-storage

# Create PR on GitHub

# Day 2: Address review comments
# Make requested changes

git add -A
git commit -m "refactor: use connection string for Azure auth"
git push

# Day 3: Update branch (main had changes)
git fetch origin
git rebase origin/main
git push --force-with-lease

# CI turns green, PR approved, merge via GitHub UI
# Use "Squash and Merge"

# Cleanup
git checkout main
git pull --rebase origin main
git branch -d feat/azure-blob-storage
```

### Example: Hotfix Flow

```bash
# Critical bug in production
git checkout main
git pull --rebase origin main
git checkout -b fix/auth-token-validation

# Fix the bug
# Edit api/auth_endpoints.py

git add api/auth_endpoints.py
git commit -m "fix: validate token presence before access"
git push -u origin fix/auth-token-validation

# Create PR with "Priority: HIGH" label
# After approval + green CI, squash merge
# Deploy immediately
```

---

## Version

**Last Updated:** October 1, 2025  
**Version:** 1.0  
**Maintainer:** BabyShield Development Team

---

**Questions or suggestions?** Open an issue or PR to improve this guide.

