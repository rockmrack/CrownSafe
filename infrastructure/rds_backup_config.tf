# =====================================================
# RDS Backup and Disaster Recovery Configuration
# =====================================================

# Primary RDS Instance with Enhanced Backup Settings
resource "aws_db_instance" "babyshield_primary" {
  identifier     = "babyshield-prod"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.r6g.xlarge"
  
  # Storage Configuration
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_type         = "gp3"
  storage_encrypted    = true
  kms_key_id          = aws_kms_key.rds_encryption.arn
  
  # Database Configuration
  db_name  = "babyshield"
  username = "babyshield_admin"
  password = var.db_master_password  # Use AWS Secrets Manager in production
  port     = 5432
  
  # Backup Configuration - CRITICAL FOR DR
  backup_retention_period   = 35  # Maximum retention for automated backups
  backup_window            = "03:00-04:00"  # UTC - low traffic period
  maintenance_window       = "sun:04:00-sun:05:00"
  copy_tags_to_snapshot    = true
  delete_automated_backups = false  # Keep backups even if instance is deleted
  
  # High Availability
  multi_az               = true
  availability_zone      = null  # Let AWS choose for Multi-AZ
  db_subnet_group_name   = aws_db_subnet_group.babyshield.name
  
  # Security
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  
  # Performance Insights
  enabled_cloudwatch_logs_exports = ["postgresql"]
  performance_insights_enabled     = true
  performance_insights_retention_period = 7
  performance_insights_kms_key_id = aws_kms_key.rds_encryption.arn
  
  # Monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_enhanced_monitoring.arn
  
  # Protection
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "babyshield-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  
  # Tags
  tags = {
    Name               = "babyshield-primary"
    Environment        = "production"
    BackupPriority     = "critical"
    DataClassification = "sensitive"
    DisasterRecovery   = "primary"
  }
  
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [password]
  }
}

# =====================================================
# Read Replica for Disaster Recovery
# =====================================================

resource "aws_db_instance" "babyshield_dr_replica" {
  identifier = "babyshield-dr-replica"
  
  # Replica Configuration
  replicate_source_db = aws_db_instance.babyshield_primary.identifier
  
  # Instance Configuration (can be smaller than primary)
  instance_class = "db.r6g.large"
  
  # Storage (inherited from primary)
  storage_encrypted = true
  
  # Different region for true DR (requires provider alias)
  # provider = aws.dr_region
  
  # Backup on replica (for additional protection)
  backup_retention_period = 7
  backup_window          = "04:00-05:00"
  
  # High Availability in DR region
  multi_az = false  # Can be single-AZ to save costs
  
  # Security
  publicly_accessible = false
  
  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql"]
  performance_insights_enabled     = true
  
  # Protection
  deletion_protection = true
  skip_final_snapshot = false
  
  tags = {
    Name               = "babyshield-dr-replica"
    Environment        = "dr"
    BackupPriority     = "critical"
    DisasterRecovery   = "replica"
  }
}

# =====================================================
# Manual Snapshots for Critical Points
# =====================================================

resource "aws_db_snapshot" "pre_deployment" {
  db_instance_identifier = aws_db_instance.babyshield_primary.identifier
  db_snapshot_identifier = "babyshield-pre-deployment-${formatdate("YYYY-MM-DD", timestamp())}"
  
  tags = {
    Name        = "Pre-deployment Snapshot"
    Type        = "manual"
    Retention   = "30-days"
    Created     = timestamp()
  }
  
  lifecycle {
    ignore_changes = [db_snapshot_identifier]
  }
}

# =====================================================
# S3 Bucket for Backup Exports
# =====================================================

resource "aws_s3_bucket" "backup_exports" {
  bucket = "babyshield-backup-exports-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name               = "babyshield-backup-exports"
    Environment        = "production"
    DataClassification = "sensitive"
    Purpose           = "rds-exports"
  }
}

# Versioning for backup integrity
resource "aws_s3_bucket_versioning" "backup_exports" {
  bucket = aws_s3_bucket.backup_exports.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption for backup exports
resource "aws_s3_bucket_server_side_encryption_configuration" "backup_exports" {
  bucket = aws_s3_bucket.backup_exports.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_backup.arn
    }
    bucket_key_enabled = true
  }
}

# Lifecycle rules for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "backup_exports" {
  bucket = aws_s3_bucket.backup_exports.id
  
  rule {
    id     = "transition-to-glacier"
    status = "Enabled"
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
    
    expiration {
      days = 2555  # 7 years for compliance
    }
  }
  
  rule {
    id     = "delete-incomplete-multipart"
    status = "Enabled"
    
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Cross-region replication for DR
resource "aws_s3_bucket_replication_configuration" "backup_exports" {
  role   = aws_iam_role.s3_replication.arn
  bucket = aws_s3_bucket.backup_exports.id
  
  rule {
    id     = "replicate-to-dr-region"
    status = "Enabled"
    
    filter {}
    
    destination {
      bucket        = aws_s3_bucket.backup_exports_dr.arn
      storage_class = "STANDARD_IA"
      
      encryption_configuration {
        replica_kms_key_id = aws_kms_key.s3_backup_dr.arn
      }
    }
    
    delete_marker_replication {
      status = "Enabled"
    }
  }
}

# =====================================================
# IAM Roles for RDS Export to S3
# =====================================================

resource "aws_iam_role" "rds_s3_export" {
  name = "rds-s3-export-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "export.rds.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Purpose = "rds-backup-export"
  }
}

resource "aws_iam_role_policy" "rds_s3_export" {
  name = "rds-s3-export-policy"
  role = aws_iam_role.rds_s3_export.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject*",
          "s3:GetObject*",
          "s3:ListBucket",
          "s3:DeleteObject*",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.backup_exports.arn,
          "${aws_s3_bucket.backup_exports.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = [
          aws_kms_key.rds_encryption.arn,
          aws_kms_key.s3_backup.arn
        ]
      }
    ]
  })
}

# =====================================================
# CloudWatch Alarms for Backup Monitoring
# =====================================================

resource "aws_cloudwatch_metric_alarm" "backup_failed" {
  alarm_name          = "rds-backup-failed"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name        = "BackupRetentionPeriodStorageUsed"
  namespace          = "AWS/RDS"
  period             = "86400"  # Daily
  statistic          = "Maximum"
  threshold          = "1"
  alarm_description  = "Alert when RDS backup fails"
  alarm_actions      = [aws_sns_topic.database_alerts.arn]
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.babyshield_primary.identifier
  }
  
  treat_missing_data = "breaching"
}

resource "aws_cloudwatch_metric_alarm" "storage_space" {
  alarm_name          = "rds-low-storage-space"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name        = "FreeStorageSpace"
  namespace          = "AWS/RDS"
  period             = "300"
  statistic          = "Average"
  threshold          = "10737418240"  # 10 GB in bytes
  alarm_description  = "Alert when RDS storage space is low"
  alarm_actions      = [aws_sns_topic.database_alerts.arn]
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.babyshield_primary.identifier
  }
}

resource "aws_cloudwatch_metric_alarm" "replica_lag" {
  alarm_name          = "rds-high-replica-lag"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "ReplicaLag"
  namespace          = "AWS/RDS"
  period             = "300"
  statistic          = "Average"
  threshold          = "30"  # 30 seconds
  alarm_description  = "Alert when replica lag is high"
  alarm_actions      = [aws_sns_topic.database_alerts.arn]
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.babyshield_dr_replica.identifier
  }
}

# =====================================================
# Lambda Function for Automated Restore Testing
# =====================================================

resource "aws_lambda_function" "restore_test" {
  filename         = "lambda/restore_test.zip"
  function_name    = "babyshield-restore-test"
  role            = aws_iam_role.lambda_restore_test.arn
  handler         = "restore_test.handler"
  source_code_hash = filebase64sha256("lambda/restore_test.zip")
  runtime         = "python3.11"
  timeout         = 900  # 15 minutes
  
  environment {
    variables = {
      SOURCE_DB_IDENTIFIER = aws_db_instance.babyshield_primary.identifier
      SNS_TOPIC_ARN       = aws_sns_topic.dr_notifications.arn
      S3_BUCKET           = aws_s3_bucket.backup_exports.id
    }
  }
  
  tags = {
    Purpose = "disaster-recovery-testing"
  }
}

# Schedule weekly restore test
resource "aws_cloudwatch_event_rule" "weekly_restore_test" {
  name                = "weekly-restore-test"
  description         = "Trigger weekly RDS restore test"
  schedule_expression = "cron(0 2 ? * SUN *)"  # Every Sunday at 2 AM UTC
  
  tags = {
    Purpose = "disaster-recovery"
  }
}

resource "aws_cloudwatch_event_target" "restore_test" {
  rule      = aws_cloudwatch_event_rule.weekly_restore_test.name
  target_id = "RestoreTestLambda"
  arn       = aws_lambda_function.restore_test.arn
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.restore_test.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_restore_test.arn
}

# =====================================================
# KMS Keys for Encryption
# =====================================================

resource "aws_kms_key" "rds_encryption" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 30
  enable_key_rotation    = true
  
  tags = {
    Name    = "babyshield-rds-encryption"
    Purpose = "database-encryption"
  }
}

resource "aws_kms_alias" "rds_encryption" {
  name          = "alias/babyshield-rds"
  target_key_id = aws_kms_key.rds_encryption.key_id
}

resource "aws_kms_key" "s3_backup" {
  description             = "KMS key for S3 backup encryption"
  deletion_window_in_days = 30
  enable_key_rotation    = true
  
  tags = {
    Name    = "babyshield-s3-backup"
    Purpose = "backup-encryption"
  }
}

resource "aws_kms_alias" "s3_backup" {
  name          = "alias/babyshield-s3-backup"
  target_key_id = aws_kms_key.s3_backup.key_id
}

# =====================================================
# Outputs for Reference
# =====================================================

output "rds_endpoint" {
  value       = aws_db_instance.babyshield_primary.endpoint
  description = "Primary database endpoint"
  sensitive   = true
}

output "dr_replica_endpoint" {
  value       = aws_db_instance.babyshield_dr_replica.endpoint
  description = "DR replica endpoint"
  sensitive   = true
}

output "backup_s3_bucket" {
  value       = aws_s3_bucket.backup_exports.id
  description = "S3 bucket for backup exports"
}

output "earliest_restorable_time" {
  value       = aws_db_instance.babyshield_primary.latest_restorable_time
  description = "Earliest point-in-time recovery available"
}

output "backup_retention_period" {
  value       = aws_db_instance.babyshield_primary.backup_retention_period
  description = "Number of days backups are retained"
}
