# Security Setup Guide

## 🔐 CRITICAL: Set Up Secrets Before Deploying

### 1. Generate Strong Secrets

```bash
# Generate SECRET_KEY (64 characters)
python -c 'import secrets; print(secrets.token_urlsafe(64))'

# Generate JWT_SECRET_KEY (64 characters)  
python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

### 2. Set Environment Variables

**Local Development (.env file):**
```bash
cp env.example .env
# Edit .env with your generated secrets
```

**Production (AWS ECS Task Definition):**
```json
{
  "secrets": [
    {
      "name": "SECRET_KEY",
      "valueFrom": "arn:aws:secretsmanager:region:account:secret:babyshield/SECRET_KEY"
    },
    {
      "name": "JWT_SECRET_KEY",
      "valueFrom": "arn:aws:secretsmanager:region:account:secret:babyshield/JWT_SECRET_KEY"
    },
    {
      "name": "DATABASE_URL",
      "valueFrom": "arn:aws:secretsmanager:region:account:secret:babyshield/DATABASE_URL"
    }
  ]
}
```

### 3. Database Credentials

**DO NOT use default credentials in production!**

Current dev defaults:
- Username: `postgres`
- Password: `postgres`

**For production:**
1. Use AWS RDS with strong password
2. Store connection string in AWS Secrets Manager
3. Set DATABASE_URL environment variable

### 4. Verify Security

```bash
# Check that secrets are loaded from environment
python -c "from core_infra.config import Config; c = Config(); assert c.SECRET_KEY != 'dev-secret-key-change-this-in-production', 'SECRET_KEY not set!'; print('✓ Secrets configured correctly')"
```

### 5. Rotate Secrets

**Schedule:** Every 90 days

```bash
# 1. Generate new secrets
# 2. Update AWS Secrets Manager
# 3. Update ECS task definition
# 4. Restart ECS service
```

---

## ⚠️ Current Status

### What's Already Secure ✅
- Environment variables properly used
- Production validation in place
- Dev defaults only for local development

### What Needs Action 🔴
1. Generate production secrets (see above)
2. Store in AWS Secrets Manager
3. Update ECS task definition
4. Document secret rotation schedule

---

## 📋 Deployment Checklist

Before deploying to production:

- [ ] Generated strong SECRET_KEY (64+ chars)
- [ ] Generated strong JWT_SECRET_KEY (64+ chars)
- [ ] Set DATABASE_URL with production credentials
- [ ] Stored all secrets in AWS Secrets Manager
- [ ] Updated ECS task definition
- [ ] Verified secrets load correctly
- [ ] Documented secret rotation schedule
- [ ] Tested application startup with production config

---

**Last Updated:** October 5, 2025

