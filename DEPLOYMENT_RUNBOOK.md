# BabyShield Backend - Production Deployment Runbook

## Overview
This runbook provides step-by-step instructions for deploying the BabyShield Backend to production AWS ECS.

## Prerequisites
- AWS CLI configured with appropriate permissions
- Docker installed locally
- Access to ECR repository: `180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend`
- Access to ECS cluster: `babyshield-cluster`
- Access to RDS instance: `babyshield-prod-db`

## Database Configuration

### PostgreSQL Setup
- **RDS Instance**: `babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com`
- **Port**: 5432
- **Database**: `babyshield_prod`
- **Credentials**: Stored in AWS Secrets Manager `babyshield/prod/database`

### Required Database Objects
The application requires the following database objects:
- `recalls_enhanced` table with `severity` and `risk_category` columns
- `pg_trgm` extension for fuzzy text search
- Proper indexes for search performance

## Deployment Steps

### 1. Build Docker Image
```bash
# Build production image
docker build -f Dockerfile.final -t babyshield-backend:production-fixed-$(date +%Y%m%d) .

# Tag for ECR
docker tag babyshield-backend:production-fixed-$(date +%Y%m%d) \
  180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-$(date +%Y%m%d)
```

### 2. Push to ECR
```bash
# Authenticate with ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin \
  180703226577.dkr.ecr.eu-north-1.amazonaws.com

# Push image
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-$(date +%Y%m%d)
```

### 3. Update ECS Task Definition
The task definition should use AWS Secrets Manager for database credentials:

```json
{
  "family": "babyshield-backend-task",
  "executionRoleArn": "arn:aws:iam::180703226577:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::180703226577:role/babyshield-task-role",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "babyshield-backend",
      "image": "180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-YYYYMMDD",
      "secrets": [
        {
          "name": "DB_USERNAME",
          "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/prod/database:username::"
        },
        {
          "name": "DB_PASSWORD", 
          "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/prod/database:password::"
        },
        {
          "name": "DB_HOST",
          "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/prod/database:host::"
        },
        {
          "name": "DB_PORT",
          "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/prod/database:port::"
        },
        {
          "name": "DB_NAME",
          "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/prod/database:dbname::"
        }
      ]
    }
  ]
}
```

### 4. Deploy to ECS
```bash
# Register new task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json --region eu-north-1

# Update service
aws ecs update-service \
  --cluster babyshield-cluster \
  --service babyshield-backend-task-service-0l41s2a9 \
  --task-definition babyshield-backend-task:REVISION \
  --region eu-north-1
```

## Post-Deployment Verification

### 1. Health Checks
Verify the following endpoints return 200 status:
- `GET /healthz` - Basic health check
- `GET /readyz` - Readiness check with database connectivity
- `GET /` - Root endpoint (should return service info)
- `GET /api/v1/version` - Version information

### 2. Search Functionality
Test the search endpoint:
```bash
curl -X POST https://babyshield-backend-alb-1130876534.eu-north-1.elb.amazonaws.com/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'
```

Expected response: 200 with search results or empty array, NOT 500.

### 3. Database Verification
Check that migrations ran successfully:
```sql
-- Connect to PostgreSQL and verify tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('recalls_enhanced', 'users');

-- Verify severity column exists
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'recalls_enhanced' AND column_name = 'severity';

-- Verify pg_trgm extension
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';
```

## Monitoring and Logs

### CloudWatch Logs
- **Log Group**: `/ecs/babyshield-backend`
- **Region**: `eu-north-1`

### Log Commands
```bash
# Get logs from last 10 minutes
aws logs filter-log-events \
  --log-group-name "/ecs/babyshield-backend" \
  --start-time $(date -d '10 minutes ago' +%s)000 \
  --region eu-north-1

# Follow logs in real-time
aws logs tail "/ecs/babyshield-backend" \
  --follow \
  --region eu-north-1 \
  --since 10m
```

### Key Metrics to Monitor
- HTTP 5xx errors by route
- Database connection errors
- Search endpoint response times
- Memory and CPU utilization

## Troubleshooting

### Common Issues

1. **500 errors on search endpoint**
   - Check if `recalls_enhanced` table exists
   - Verify `severity` column is present
   - Check if `pg_trgm` extension is installed

2. **Database connection failures**
   - Verify RDS instance is running
   - Check security group allows connections from ECS
   - Verify credentials in Secrets Manager

3. **Migration failures**
   - Check Alembic configuration
   - Verify database permissions
   - Check for conflicting migrations

### Rollback Procedure
If deployment fails:
```bash
# Rollback to previous task definition
aws ecs update-service \
  --cluster babyshield-cluster \
  --service babyshield-backend-task-service-0l41s2a9 \
  --task-definition babyshield-backend-task:PREVIOUS_REVISION \
  --region eu-north-1
```

## Security Considerations

### Production Requirements
- **NEVER** use SQLite in production
- Database credentials must be stored in AWS Secrets Manager
- All environment variables should be validated on startup
- Logs should not contain sensitive information

### Configuration Validation
The application validates:
- PostgreSQL database URL in production
- Secret key is not default value
- Required environment variables are present

## Maintenance

### Regular Tasks
- Monitor CloudWatch logs for errors
- Check database performance metrics
- Update dependencies regularly
- Review and rotate secrets periodically

### Database Maintenance
- Run `VACUUM ANALYZE` on search tables weekly
- Monitor index usage and performance
- Backup database regularly

## Contact Information
For issues or questions:
- Check CloudWatch logs first
- Review this runbook
- Contact DevOps team if needed
