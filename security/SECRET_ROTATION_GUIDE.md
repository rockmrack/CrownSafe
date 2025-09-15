# Secret Rotation Guide

## Overview
This guide outlines the procedures for rotating secrets and API keys in the BabyShield application.

**Critical**: All secrets must be rotated every 90 days or immediately if compromised.

---

## 🔑 Secret Inventory

| Secret Name | Type | Location | Rotation Schedule | Last Rotated |
|------------|------|----------|-------------------|--------------|
| `DATABASE_URL` | PostgreSQL | AWS RDS | 90 days | _________ |
| `REDIS_URL` | Redis Connection | AWS ElastiCache | 90 days | _________ |
| `JWT_SECRET_KEY` | JWT Signing | Environment | 30 days | _________ |
| `AWS_ACCESS_KEY_ID` | AWS API | IAM | 60 days | _________ |
| `AWS_SECRET_ACCESS_KEY` | AWS API | IAM | 60 days | _________ |
| `GOOGLE_CLOUD_API_KEY` | Google Vision | GCP | 90 days | _________ |
| `OPENAI_API_KEY` | OpenAI | OpenAI | 90 days | _________ |
| `STRIPE_SECRET_KEY` | Stripe | Stripe Dashboard | 90 days | _________ |
| `APPLE_SHARED_SECRET` | IAP | App Store Connect | Never | _________ |
| `GOOGLE_PLAY_SERVICE_KEY` | Google Play | Play Console | 90 days | _________ |
| `SENTRY_DSN` | Error Tracking | Sentry | Never | _________ |
| `ENCRYPTION_KEY` | Data Encryption | AWS KMS | 365 days | _________ |

---

## 🔄 Rotation Procedures

### 1. Database Password Rotation

```bash
#!/bin/bash
# rotate_db_password.sh

# Step 1: Generate new password
NEW_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
echo "New password generated: $NEW_PASSWORD"

# Step 2: Update RDS password
aws rds modify-db-instance \
  --db-instance-identifier babyshield-prod \
  --master-user-password "$NEW_PASSWORD" \
  --apply-immediately \
  --region eu-north-1

# Step 3: Wait for RDS to apply changes
echo "Waiting for RDS to apply changes (this may take 5-10 minutes)..."
aws rds wait db-instance-available \
  --db-instance-identifier babyshield-prod \
  --region eu-north-1

# Step 4: Update environment variables in ECS
aws ecs update-task-definition \
  --family babyshield-task \
  --region eu-north-1 \
  --container-definitions "[{
    \"name\": \"babyshield-api\",
    \"environment\": [{
      \"name\": \"DATABASE_URL\",
      \"value\": \"postgresql://babyshield_app:${NEW_PASSWORD}@babyshield-prod.xxx.rds.amazonaws.com:5432/babyshield\"
    }]
  }]"

# Step 5: Force new deployment
aws ecs update-service \
  --cluster babyshield-cluster \
  --service babyshield-service \
  --force-new-deployment \
  --region eu-north-1

echo "Database password rotation complete!"
```

### 2. JWT Secret Rotation (Zero-Downtime)

```python
# rotate_jwt_secret.py
import os
import time
import boto3
import secrets
from datetime import datetime, timedelta

def rotate_jwt_secret():
    """
    Zero-downtime JWT secret rotation using dual-key strategy
    """
    
    # Step 1: Generate new secret
    new_secret = secrets.token_urlsafe(64)
    old_secret = os.environ.get('JWT_SECRET_KEY')
    
    # Step 2: Set both old and new secrets (grace period)
    os.environ['JWT_SECRET_KEY'] = new_secret
    os.environ['JWT_SECRET_KEY_OLD'] = old_secret
    
    print(f"Grace period started at {datetime.now()}")
    print("Both old and new tokens will be accepted for 24 hours")
    
    # Step 3: Update AWS Systems Manager Parameter Store
    ssm = boto3.client('ssm', region_name='eu-north-1')
    
    ssm.put_parameter(
        Name='/babyshield/prod/JWT_SECRET_KEY',
        Value=new_secret,
        Type='SecureString',
        Overwrite=True
    )
    
    ssm.put_parameter(
        Name='/babyshield/prod/JWT_SECRET_KEY_OLD',
        Value=old_secret,
        Type='SecureString',
        Overwrite=True
    )
    
    # Step 4: Deploy with dual-key support
    print("Deploy application with dual JWT key support")
    
    # Step 5: After 24 hours, remove old key
    print("Schedule removal of JWT_SECRET_KEY_OLD after 24 hours")
    
    return {
        'new_secret': new_secret,
        'rotation_time': datetime.now().isoformat(),
        'grace_period_ends': (datetime.now() + timedelta(hours=24)).isoformat()
    }

if __name__ == "__main__":
    result = rotate_jwt_secret()
    print(f"JWT rotation complete: {result}")
```

### 3. AWS IAM Key Rotation

```bash
#!/bin/bash
# rotate_aws_keys.sh

# Step 1: Create new access key
NEW_KEY_OUTPUT=$(aws iam create-access-key --user-name babyshield-api-user)
NEW_ACCESS_KEY=$(echo $NEW_KEY_OUTPUT | jq -r '.AccessKey.AccessKeyId')
NEW_SECRET_KEY=$(echo $NEW_KEY_OUTPUT | jq -r '.AccessKey.SecretAccessKey')

echo "New AWS keys created"

# Step 2: Update ECS task definition with new keys
aws ecs update-task-definition \
  --family babyshield-task \
  --region eu-north-1 \
  --container-definitions "[{
    \"name\": \"babyshield-api\",
    \"environment\": [
      {\"name\": \"AWS_ACCESS_KEY_ID\", \"value\": \"${NEW_ACCESS_KEY}\"},
      {\"name\": \"AWS_SECRET_ACCESS_KEY\", \"value\": \"${NEW_SECRET_KEY}\"}
    ]
  }]"

# Step 3: Deploy new task
aws ecs update-service \
  --cluster babyshield-cluster \
  --service babyshield-service \
  --force-new-deployment \
  --region eu-north-1

# Step 4: Wait for deployment
echo "Waiting for deployment to complete..."
sleep 300  # 5 minutes

# Step 5: Delete old access key
OLD_ACCESS_KEY=$(aws iam list-access-keys --user-name babyshield-api-user \
  | jq -r '.AccessKeyMetadata[] | select(.AccessKeyId != "'$NEW_ACCESS_KEY'") | .AccessKeyId')

if [ ! -z "$OLD_ACCESS_KEY" ]; then
  aws iam delete-access-key --user-name babyshield-api-user --access-key-id $OLD_ACCESS_KEY
  echo "Old key deleted: $OLD_ACCESS_KEY"
fi

echo "AWS key rotation complete!"
```

### 4. API Key Rotation (Third-Party Services)

```python
# rotate_api_keys.py
import os
import requests
from datetime import datetime
import boto3

class APIKeyRotator:
    """Rotate third-party API keys"""
    
    def __init__(self):
        self.ssm = boto3.client('ssm', region_name='eu-north-1')
    
    def rotate_google_cloud_key(self):
        """Rotate Google Cloud Vision API key"""
        # Note: This requires manual steps in GCP Console
        print("Google Cloud API Key Rotation:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Create new API key with same restrictions")
        print("3. Update the key below:")
        
        new_key = input("Enter new Google Cloud API key: ").strip()
        
        # Store in Parameter Store
        self.ssm.put_parameter(
            Name='/babyshield/prod/GOOGLE_CLOUD_API_KEY',
            Value=new_key,
            Type='SecureString',
            Overwrite=True
        )
        
        return new_key
    
    def rotate_openai_key(self):
        """Rotate OpenAI API key"""
        print("OpenAI API Key Rotation:")
        print("1. Go to https://platform.openai.com/api-keys")
        print("2. Create new secret key")
        print("3. Update the key below:")
        
        new_key = input("Enter new OpenAI API key: ").strip()
        
        # Store in Parameter Store
        self.ssm.put_parameter(
            Name='/babyshield/prod/OPENAI_API_KEY',
            Value=new_key,
            Type='SecureString',
            Overwrite=True
        )
        
        return new_key
    
    def rotate_stripe_key(self):
        """Rotate Stripe API key"""
        print("Stripe API Key Rotation:")
        print("1. Go to https://dashboard.stripe.com/apikeys")
        print("2. Roll secret key")
        print("3. Update the key below:")
        
        new_key = input("Enter new Stripe secret key: ").strip()
        
        # Store in Parameter Store
        self.ssm.put_parameter(
            Name='/babyshield/prod/STRIPE_SECRET_KEY',
            Value=new_key,
            Type='SecureString',
            Overwrite=True
        )
        
        return new_key

if __name__ == "__main__":
    rotator = APIKeyRotator()
    
    print("API Key Rotation Tool")
    print("1. Google Cloud Vision")
    print("2. OpenAI")
    print("3. Stripe")
    print("4. All")
    
    choice = input("Select service to rotate (1-4): ")
    
    if choice == "1":
        rotator.rotate_google_cloud_key()
    elif choice == "2":
        rotator.rotate_openai_key()
    elif choice == "3":
        rotator.rotate_stripe_key()
    elif choice == "4":
        rotator.rotate_google_cloud_key()
        rotator.rotate_openai_key()
        rotator.rotate_stripe_key()
```

---

## 🔐 AWS Systems Manager Parameter Store

### Setup Secrets in Parameter Store

```bash
# Store all secrets in Parameter Store (one-time setup)
aws ssm put-parameter \
  --name "/babyshield/prod/DATABASE_URL" \
  --value "postgresql://user:pass@host:5432/db" \
  --type "SecureString" \
  --key-id "alias/aws/ssm" \
  --region eu-north-1

aws ssm put-parameter \
  --name "/babyshield/prod/JWT_SECRET_KEY" \
  --value "your-jwt-secret" \
  --type "SecureString" \
  --region eu-north-1

aws ssm put-parameter \
  --name "/babyshield/prod/REDIS_URL" \
  --value "redis://host:6379" \
  --type "SecureString" \
  --region eu-north-1

# Continue for all secrets...
```

### Retrieve Secrets in Application

```python
# config/secrets.py
import boto3
import os
from functools import lru_cache

@lru_cache(maxsize=128)
def get_secret(secret_name: str, default=None):
    """Get secret from AWS Parameter Store or environment"""
    
    # Try environment variable first (for local development)
    env_value = os.environ.get(secret_name)
    if env_value:
        return env_value
    
    # Get from Parameter Store in production
    try:
        ssm = boto3.client('ssm', region_name='eu-north-1')
        parameter = ssm.get_parameter(
            Name=f'/babyshield/prod/{secret_name}',
            WithDecryption=True
        )
        return parameter['Parameter']['Value']
    except Exception as e:
        print(f"Warning: Could not retrieve secret {secret_name}: {e}")
        return default

# Usage
DATABASE_URL = get_secret('DATABASE_URL')
JWT_SECRET_KEY = get_secret('JWT_SECRET_KEY')
REDIS_URL = get_secret('REDIS_URL')
```

---

## 📅 Rotation Schedule

### Automated Rotation with AWS Lambda

```python
# lambda_secret_rotator.py
import boto3
import json
from datetime import datetime, timedelta

def lambda_handler(event, context):
    """
    AWS Lambda function to check and notify about secret rotation
    Runs daily via CloudWatch Events
    """
    
    ssm = boto3.client('ssm')
    sns = boto3.client('sns')
    
    # Define rotation schedules (in days)
    rotation_schedule = {
        'JWT_SECRET_KEY': 30,
        'DATABASE_URL': 90,
        'AWS_ACCESS_KEY_ID': 60,
        'GOOGLE_CLOUD_API_KEY': 90,
        'OPENAI_API_KEY': 90,
        'STRIPE_SECRET_KEY': 90,
    }
    
    alerts = []
    
    for secret_name, rotation_days in rotation_schedule.items():
        try:
            # Get parameter metadata
            response = ssm.describe_parameters(
                Filters=[
                    {'Key': 'Name', 'Values': [f'/babyshield/prod/{secret_name}']}
                ]
            )
            
            if response['Parameters']:
                param = response['Parameters'][0]
                last_modified = param['LastModifiedDate']
                
                # Check if rotation is needed
                days_since_rotation = (datetime.now(last_modified.tzinfo) - last_modified).days
                
                if days_since_rotation >= rotation_days:
                    alerts.append(f"⚠️ {secret_name}: Overdue ({days_since_rotation} days)")
                elif days_since_rotation >= rotation_days - 7:
                    alerts.append(f"⏰ {secret_name}: Due soon ({rotation_days - days_since_rotation} days left)")
        
        except Exception as e:
            alerts.append(f"❌ {secret_name}: Error checking - {str(e)}")
    
    # Send alerts if any
    if alerts:
        message = "Secret Rotation Alert\n\n" + "\n".join(alerts)
        
        sns.publish(
            TopicArn='arn:aws:sns:eu-north-1:180703226577:babyshield-security-alerts',
            Subject='BabyShield Secret Rotation Required',
            Message=message
        )
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'checked': len(rotation_schedule),
            'alerts': len(alerts)
        })
    }
```

---

## 🚨 Emergency Rotation Procedure

### In Case of Compromise

1. **Immediate Actions** (< 5 minutes)
   ```bash
   # Disable compromised credentials immediately
   aws iam update-access-key --access-key-id COMPROMISED_KEY --status Inactive --user-name babyshield-api-user
   
   # Revoke database sessions
   psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = 'babyshield_app';"
   ```

2. **Rotate All Affected Secrets** (< 30 minutes)
   ```bash
   # Run emergency rotation script
   ./scripts/emergency_rotate_all.sh
   ```

3. **Audit Access** (< 1 hour)
   ```bash
   # Check CloudTrail for unauthorized access
   aws cloudtrail lookup-events --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=COMPROMISED_KEY
   ```

4. **Update WAF Rules** (< 1 hour)
   ```bash
   # Block suspicious IPs
   aws wafv2 update-ip-set --scope REGIONAL --name babyshield-blocked-ips --addresses "SUSPICIOUS_IP/32"
   ```

5. **Notify** (< 2 hours)
   - Security team
   - DevOps team
   - Compliance officer
   - Legal team (if user data affected)

---

## 🛡️ Best Practices

### DO's
- ✅ Use AWS Systems Manager Parameter Store or Secrets Manager
- ✅ Enable automatic rotation where possible
- ✅ Use different secrets for different environments
- ✅ Implement grace periods for JWT rotation
- ✅ Audit secret access via CloudTrail
- ✅ Use IAM roles instead of keys where possible
- ✅ Encrypt secrets at rest and in transit
- ✅ Monitor for exposed secrets in code (git-secrets)

### DON'Ts
- ❌ Store secrets in code or git
- ❌ Use the same secret across environments
- ❌ Share secrets via email or Slack
- ❌ Log secret values
- ❌ Use weak or predictable secrets
- ❌ Ignore rotation schedules
- ❌ Keep inactive keys
- ❌ Use root AWS credentials

---

## 📊 Rotation Tracking

### Monthly Rotation Report

| Month | Secrets Rotated | On Schedule | Overdue | Emergency |
|-------|-----------------|-------------|---------|-----------|
| Jan 2024 | 12 | 10 | 2 | 0 |
| Feb 2024 | 8 | 8 | 0 | 0 |
| Mar 2024 | 15 | 13 | 1 | 1 |

---

## 🔍 Validation

### Post-Rotation Checklist

- [ ] Old credentials deactivated
- [ ] New credentials working in production
- [ ] No service interruptions
- [ ] Audit logs reviewed
- [ ] Documentation updated
- [ ] Team notified
- [ ] Next rotation scheduled
- [ ] Backup credentials stored securely

---

## 📞 Contacts

**Security Team Lead:** security@babyshield.app  
**DevOps On-Call:** +XX-XXXX-XXXX  
**AWS Support:** Premium Support Case  

---

**Last Updated:** January 2024  
**Next Review:** April 2024  
**Version:** 1.0.0
