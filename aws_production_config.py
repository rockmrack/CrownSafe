"""
AWS Production Configuration Template
Essential settings for handling 1000+ concurrent users
"""

import os

# ============================================================
# CRITICAL AWS PRODUCTION SETTINGS
# Copy these to your .env file with actual values
# ============================================================

PRODUCTION_ENV = """
# === DATABASE (RDS PostgreSQL) ===
DATABASE_URL=postgresql://username:password@your-rds-endpoint.amazonaws.com:5432/babyshield
DATABASE_POOL_SIZE=100  # Increased for production
DATABASE_MAX_OVERFLOW=200
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
DATABASE_ENGINE_ECHO=False

# === REDIS (ElastiCache) ===
REDIS_URL=redis://your-elasticache-endpoint.cache.amazonaws.com:6379/0
REDIS_POOL_SIZE=50
REDIS_MAX_CONNECTIONS=200
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_KEEPALIVE=True
REDIS_SOCKET_KEEPALIVE_OPTIONS={}
REDIS_CACHE_TTL=300  # 5 minutes for production

# === AWS SERVICES ===
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=babyshield-prod-assets
S3_BUCKET_REGION=us-east-1
CLOUDFRONT_DISTRIBUTION_ID=your-distribution-id
CLOUDFRONT_DOMAIN=d1234567890.cloudfront.net

# === API CONFIGURATION ===
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4  # Per container, ECS will scale containers
WORKER_CLASS=uvicorn.workers.UvicornWorker
WORKER_CONNECTIONS=1000
WORKER_TIMEOUT=30
GRACEFUL_TIMEOUT=30
KEEPALIVE=5

# === SECURITY ===
SECRET_KEY=generate-strong-random-key-here
JWT_SECRET_KEY=another-strong-random-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
ALLOWED_ORIGINS=https://app.babyshield.com,https://www.babyshield.com
SECURE_COOKIES=True
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=lax

# === RATE LIMITING ===
RATE_LIMIT_ENABLED=True
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_STORAGE_URL=redis://your-elasticache-endpoint.cache.amazonaws.com:6379/1

# === MONITORING ===
SENTRY_DSN=your-sentry-dsn
DATADOG_API_KEY=your-datadog-key
DATADOG_APP_KEY=your-datadog-app-key
LOG_LEVEL=WARNING  # INFO for debugging, WARNING for production
ENABLE_METRICS=True
ENABLE_TRACING=True

# === EXTERNAL APIS ===
GOOGLE_VISION_API_KEY=your-api-key
CPSC_API_KEY=your-api-key
OPENAI_API_KEY=your-api-key

# === CELERY (SQS) ===
CELERY_BROKER_URL=sqs://
CELERY_RESULT_BACKEND=redis://your-elasticache-endpoint.cache.amazonaws.com:6379/2
CELERY_TASK_ALWAYS_EAGER=False
CELERY_TASK_EAGER_PROPAGATES=False
CELERY_WORKER_PREFETCH_MULTIPLIER=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
CELERY_WORKER_DISABLE_RATE_LIMITS=False
CELERY_TASK_SOFT_TIME_LIMIT=300
CELERY_TASK_TIME_LIMIT=600

# === FEATURE FLAGS ===
ENABLE_RATE_LIMITING=True
ENABLE_AUTHENTICATION=True
ENABLE_CACHE=True
ENABLE_ASYNC_PROCESSING=True
ENABLE_MONITORING=True
DEBUG=False
"""

# ============================================================
# ECS TASK DEFINITION
# ============================================================

ECS_TASK_DEFINITION = {
    "family": "babyshield-api",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "2048",  # 2 vCPU
    "memory": "4096",  # 4 GB
    "containerDefinitions": [
        {
            "name": "babyshield-api",
            "image": "your-ecr-repo/babyshield:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {"name": "PORT", "value": "8000"},
                {"name": "WORKERS", "value": "4"},
            ],
            "secrets": [
                {
                    "name": "DATABASE_URL",
                    "valueFrom": "arn:aws:secretsmanager:region:account:secret:babyshield/db"
                },
                {
                    "name": "JWT_SECRET_KEY",
                    "valueFrom": "arn:aws:secretsmanager:region:account:secret:babyshield/jwt"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/babyshield",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "api"
                }
            },
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            }
        }
    ]
}

# ============================================================
# AUTO-SCALING CONFIGURATION
# ============================================================

AUTO_SCALING_CONFIG = {
    "min_capacity": 2,  # Minimum 2 containers
    "max_capacity": 20,  # Scale up to 20 containers
    "target_tracking_scaling_policies": [
        {
            "name": "cpu-scaling",
            "target_value": 70.0,
            "predefined_metric_type": "ECSServiceAverageCPUUtilization",
            "scale_in_cooldown": 300,
            "scale_out_cooldown": 60
        },
        {
            "name": "memory-scaling",
            "target_value": 80.0,
            "predefined_metric_type": "ECSServiceAverageMemoryUtilization",
            "scale_in_cooldown": 300,
            "scale_out_cooldown": 60
        }
    ]
}

# ============================================================
# CLOUDFORMATION TEMPLATE SNIPPET
# ============================================================

CLOUDFORMATION_RESOURCES = """
Resources:
  # RDS PostgreSQL with Read Replica
  DatabaseCluster:
    Type: AWS::RDS::DBCluster
    Properties:
      Engine: aurora-postgresql
      EngineVersion: '13.7'
      MasterUsername: !Ref DBUsername
      MasterUserPassword: !Ref DBPassword
      DatabaseName: babyshield
      DBClusterParameterGroupName: default.aurora-postgresql13
      BackupRetentionPeriod: 7
      PreferredBackupWindow: "03:00-04:00"
      PreferredMaintenanceWindow: "sun:04:00-sun:05:00"
      
  DatabaseInstance1:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceClass: db.r6g.large
      DBClusterIdentifier: !Ref DatabaseCluster
      Engine: aurora-postgresql
      
  DatabaseInstance2:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceClass: db.r6g.large
      DBClusterIdentifier: !Ref DatabaseCluster
      Engine: aurora-postgresql
      
  # ElastiCache Redis Cluster
  CacheCluster:
    Type: AWS::ElastiCache::ReplicationGroup
    Properties:
      ReplicationGroupId: babyshield-cache
      ReplicationGroupDescription: BabyShield Redis Cache
      Engine: redis
      CacheNodeType: cache.r6g.large
      NumCacheClusters: 3
      AutomaticFailoverEnabled: true
      MultiAZEnabled: true
      
  # Application Load Balancer
  LoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Type: application
      Scheme: internet-facing
      SecurityGroups:
        - !Ref LoadBalancerSecurityGroup
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
        
  # ECS Cluster
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: babyshield-cluster
      CapacityProviders:
        - FARGATE
        - FARGATE_SPOT
      DefaultCapacityProviderStrategy:
        - CapacityProvider: FARGATE
          Weight: 1
        - CapacityProvider: FARGATE_SPOT
          Weight: 4
"""

print("✅ AWS Production configuration template created!")
print("\n📋 CRITICAL STEPS BEFORE DEPLOYMENT:")
print("  1. Copy PRODUCTION_ENV to .env file")
print("  2. Replace all placeholder values with actual AWS resources")
print("  3. Set up AWS Secrets Manager for sensitive values")
print("  4. Create RDS Aurora cluster with read replicas")
print("  5. Set up ElastiCache Redis cluster")
print("  6. Configure S3 bucket with CloudFront CDN")
print("  7. Deploy using ECS Fargate with auto-scaling")
print("  8. Set up CloudWatch alarms and dashboards")
print("  9. Configure WAF for DDoS protection")
print("  10. Run load testing with 1000+ concurrent users")
print("\n⚠️ DO NOT deploy without completing these steps!")
