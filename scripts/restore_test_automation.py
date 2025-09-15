#!/usr/bin/env python3
"""
Automated Database Restore Testing
Performs weekly restore drills and validates data integrity
"""

import boto3
import psycopg2
import time
import datetime
import json
import os
import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RestoreTestResult:
    """Results from a restore test"""
    success: bool
    duration_minutes: float
    snapshot_id: str
    test_instance_id: str
    validation_results: Dict
    error_message: Optional[str] = None


class RestoreTester:
    """Automated RDS restore testing"""
    
    def __init__(self, region: str = 'eu-north-1'):
        self.region = region
        self.rds = boto3.client('rds', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.source_db = os.environ.get('SOURCE_DB_ID', 'babyshield-prod')
        self.test_prefix = 'babyshield-test-restore'
        
    def get_latest_snapshot(self) -> Optional[str]:
        """Get the most recent automated snapshot"""
        
        try:
            response = self.rds.describe_db_snapshots(
                DBInstanceIdentifier=self.source_db,
                SnapshotType='automated',
                MaxRecords=10
            )
            
            if not response['DBSnapshots']:
                logger.error("No automated snapshots found")
                return None
            
            # Sort by creation time and get the latest
            snapshots = sorted(
                response['DBSnapshots'],
                key=lambda x: x['SnapshotCreateTime'],
                reverse=True
            )
            
            latest = snapshots[0]
            logger.info(f"Latest snapshot: {latest['DBSnapshotIdentifier']}")
            logger.info(f"Snapshot time: {latest['SnapshotCreateTime']}")
            
            return latest['DBSnapshotIdentifier']
            
        except Exception as e:
            logger.error(f"Error getting snapshots: {e}")
            return None
    
    def create_test_restore(self, snapshot_id: str) -> Optional[str]:
        """Create a test instance from snapshot"""
        
        test_instance_id = f"{self.test_prefix}-{int(time.time())}"
        
        try:
            logger.info(f"Creating test instance: {test_instance_id}")
            
            response = self.rds.restore_db_instance_from_db_snapshot(
                DBInstanceIdentifier=test_instance_id,
                DBSnapshotIdentifier=snapshot_id,
                DBInstanceClass='db.t3.small',  # Use smaller instance for testing
                PubliclyAccessible=False,
                MultiAZ=False,  # Single AZ for test
                StorageEncrypted=True,
                CopyTagsToSnapshot=True,
                DeletionProtection=False,  # Allow deletion after test
                Tags=[
                    {'Key': 'Purpose', 'Value': 'restore-test'},
                    {'Key': 'AutoDelete', 'Value': 'true'},
                    {'Key': 'CreatedBy', 'Value': 'restore-tester'}
                ]
            )
            
            logger.info("Restore initiated, waiting for completion...")
            return test_instance_id
            
        except Exception as e:
            logger.error(f"Error creating restore: {e}")
            return None
    
    def wait_for_instance(self, instance_id: str, timeout_minutes: int = 30) -> bool:
        """Wait for instance to be available"""
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while (time.time() - start_time) < timeout_seconds:
            try:
                response = self.rds.describe_db_instances(
                    DBInstanceIdentifier=instance_id
                )
                
                if response['DBInstances']:
                    status = response['DBInstances'][0]['DBInstanceStatus']
                    logger.info(f"Instance status: {status}")
                    
                    if status == 'available':
                        return True
                    elif status in ['failed', 'deleted']:
                        logger.error(f"Instance entered failed state: {status}")
                        return False
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error checking instance status: {e}")
                return False
        
        logger.error(f"Timeout waiting for instance after {timeout_minutes} minutes")
        return False
    
    def get_connection_info(self, instance_id: str) -> Optional[Dict]:
        """Get connection details for test instance"""
        
        try:
            response = self.rds.describe_db_instances(
                DBInstanceIdentifier=instance_id
            )
            
            if response['DBInstances']:
                instance = response['DBInstances'][0]
                return {
                    'endpoint': instance['Endpoint']['Address'],
                    'port': instance['Endpoint']['Port'],
                    'database': instance.get('DBName', 'babyshield'),
                    'username': instance.get('MasterUsername', 'babyshield_admin')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting connection info: {e}")
            return None
    
    def validate_restored_data(self, connection_info: Dict) -> Dict:
        """Validate the restored database"""
        
        validation_results = {
            'tables_exist': False,
            'row_counts': {},
            'data_integrity': True,
            'recent_data': False,
            'indexes_present': False,
            'constraints_valid': False
        }
        
        try:
            # Connect to the restored database
            conn = psycopg2.connect(
                host=connection_info['endpoint'],
                port=connection_info['port'],
                database=connection_info['database'],
                user=connection_info['username'],
                password=os.environ.get('DB_PASSWORD', 'password')
            )
            
            cursor = conn.cursor()
            
            # 1. Check if critical tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                  AND table_name IN ('users', 'recalls_enhanced', 'subscriptions', 'family_members')
                ORDER BY table_name
            """)
            
            tables = cursor.fetchall()
            validation_results['tables_exist'] = len(tables) == 4
            
            # 2. Get row counts for critical tables
            for table in ['users', 'recalls_enhanced', 'subscriptions', 'family_members']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                validation_results['row_counts'][table] = count
                logger.info(f"Table {table}: {count} rows")
            
            # 3. Check data recency
            cursor.execute("""
                SELECT MAX(created_at) as latest,
                       NOW() - MAX(created_at) as age
                FROM recalls_enhanced
            """)
            
            result = cursor.fetchone()
            if result and result[0]:
                age_hours = result[1].total_seconds() / 3600 if result[1] else 0
                validation_results['recent_data'] = age_hours < 48  # Data within 48 hours
                logger.info(f"Most recent data: {age_hours:.1f} hours old")
            
            # 4. Check for orphaned records (data integrity)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM family_members fm
                LEFT JOIN users u ON fm.user_id = u.id
                WHERE u.id IS NULL
            """)
            
            orphaned = cursor.fetchone()[0]
            validation_results['data_integrity'] = orphaned == 0
            if orphaned > 0:
                logger.warning(f"Found {orphaned} orphaned family members")
            
            # 5. Check indexes
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pg_indexes
                WHERE schemaname = 'public'
            """)
            
            index_count = cursor.fetchone()[0]
            validation_results['indexes_present'] = index_count > 10
            logger.info(f"Found {index_count} indexes")
            
            # 6. Check constraints
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.table_constraints
                WHERE constraint_schema = 'public'
                  AND constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE')
            """)
            
            constraint_count = cursor.fetchone()[0]
            validation_results['constraints_valid'] = constraint_count > 5
            logger.info(f"Found {constraint_count} constraints")
            
            cursor.close()
            conn.close()
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Error validating data: {e}")
            validation_results['error'] = str(e)
            return validation_results
    
    def cleanup_test_instance(self, instance_id: str) -> bool:
        """Delete the test instance"""
        
        try:
            logger.info(f"Deleting test instance: {instance_id}")
            
            self.rds.delete_db_instance(
                DBInstanceIdentifier=instance_id,
                SkipFinalSnapshot=True,
                DeleteAutomatedBackups=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting test instance: {e}")
            return False
    
    def send_notification(self, result: RestoreTestResult):
        """Send SNS notification with test results"""
        
        topic_arn = os.environ.get('SNS_TOPIC_ARN')
        if not topic_arn:
            logger.warning("No SNS topic configured")
            return
        
        # Format message
        if result.success:
            subject = "✅ Weekly Restore Test Successful"
            message = f"""
Weekly database restore test completed successfully.

Test Details:
- Snapshot: {result.snapshot_id}
- Test Instance: {result.test_instance_id}
- Duration: {result.duration_minutes:.1f} minutes

Validation Results:
- Tables Verified: {result.validation_results.get('tables_exist', False)}
- Total Records: {sum(result.validation_results.get('row_counts', {}).values())}
- Data Integrity: {result.validation_results.get('data_integrity', False)}
- Recent Data: {result.validation_results.get('recent_data', False)}
- Indexes Present: {result.validation_results.get('indexes_present', False)}
- Constraints Valid: {result.validation_results.get('constraints_valid', False)}

Row Counts:
{json.dumps(result.validation_results.get('row_counts', {}), indent=2)}

The test instance has been deleted.
"""
        else:
            subject = "❌ Weekly Restore Test Failed"
            message = f"""
Weekly database restore test FAILED.

Error: {result.error_message}

Please investigate immediately.
"""
        
        try:
            self.sns.publish(
                TopicArn=topic_arn,
                Subject=subject,
                Message=message
            )
            logger.info("Notification sent")
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def record_metrics(self, result: RestoreTestResult):
        """Record metrics to CloudWatch"""
        
        try:
            # Success metric
            self.cloudwatch.put_metric_data(
                Namespace='BabyShield/DR',
                MetricData=[
                    {
                        'MetricName': 'RestoreTestSuccess',
                        'Value': 1 if result.success else 0,
                        'Unit': 'None',
                        'Timestamp': datetime.datetime.utcnow()
                    },
                    {
                        'MetricName': 'RestoreTestDuration',
                        'Value': result.duration_minutes,
                        'Unit': 'Minutes',
                        'Timestamp': datetime.datetime.utcnow()
                    }
                ]
            )
            
            # Record row counts
            for table, count in result.validation_results.get('row_counts', {}).items():
                self.cloudwatch.put_metric_data(
                    Namespace='BabyShield/DR',
                    MetricData=[
                        {
                            'MetricName': 'RestoreRowCount',
                            'Value': count,
                            'Unit': 'Count',
                            'Dimensions': [
                                {'Name': 'Table', 'Value': table}
                            ],
                            'Timestamp': datetime.datetime.utcnow()
                        }
                    ]
                )
            
            logger.info("Metrics recorded to CloudWatch")
            
        except Exception as e:
            logger.error(f"Error recording metrics: {e}")
    
    def run_restore_test(self) -> RestoreTestResult:
        """Run a complete restore test"""
        
        start_time = time.time()
        test_instance_id = None
        
        try:
            # Step 1: Get latest snapshot
            snapshot_id = self.get_latest_snapshot()
            if not snapshot_id:
                raise Exception("No snapshot available for testing")
            
            # Step 2: Create test restore
            test_instance_id = self.create_test_restore(snapshot_id)
            if not test_instance_id:
                raise Exception("Failed to create test restore")
            
            # Step 3: Wait for instance to be ready
            if not self.wait_for_instance(test_instance_id):
                raise Exception("Test instance failed to become available")
            
            # Step 4: Get connection info
            connection_info = self.get_connection_info(test_instance_id)
            if not connection_info:
                raise Exception("Failed to get connection info")
            
            # Step 5: Validate data
            validation_results = self.validate_restored_data(connection_info)
            
            # Step 6: Check if validation passed
            validation_passed = (
                validation_results.get('tables_exist', False) and
                validation_results.get('data_integrity', False) and
                len(validation_results.get('row_counts', {})) > 0
            )
            
            # Calculate duration
            duration_minutes = (time.time() - start_time) / 60
            
            # Create result
            result = RestoreTestResult(
                success=validation_passed,
                duration_minutes=duration_minutes,
                snapshot_id=snapshot_id,
                test_instance_id=test_instance_id,
                validation_results=validation_results
            )
            
            logger.info(f"Restore test {'PASSED' if validation_passed else 'FAILED'}")
            
            return result
            
        except Exception as e:
            logger.error(f"Restore test failed: {e}")
            
            duration_minutes = (time.time() - start_time) / 60
            
            return RestoreTestResult(
                success=False,
                duration_minutes=duration_minutes,
                snapshot_id=snapshot_id if 'snapshot_id' in locals() else 'unknown',
                test_instance_id=test_instance_id or 'none',
                validation_results={},
                error_message=str(e)
            )
        
        finally:
            # Always cleanup test instance
            if test_instance_id:
                self.cleanup_test_instance(test_instance_id)


def main():
    """Main entry point"""
    
    logger.info("="*60)
    logger.info(" AUTOMATED RESTORE TEST STARTING")
    logger.info(f" Time: {datetime.datetime.utcnow().isoformat()}")
    logger.info("="*60)
    
    # Create tester
    tester = RestoreTester()
    
    # Run test
    result = tester.run_restore_test()
    
    # Send notification
    tester.send_notification(result)
    
    # Record metrics
    tester.record_metrics(result)
    
    # Print summary
    logger.info("="*60)
    logger.info(" TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Success: {result.success}")
    logger.info(f"Duration: {result.duration_minutes:.1f} minutes")
    logger.info(f"Validation: {json.dumps(result.validation_results, indent=2)}")
    
    # Exit with appropriate code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
