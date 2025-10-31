#!/usr/bin/env python3
"""S3 Backup Export Manager
Exports RDS snapshots to S3 for long-term storage and compliance.
"""

import datetime
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import timezone
from enum import Enum

import boto3

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ExportStatus(Enum):
    """Export task status."""

    STARTING = "STARTING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ExportTask:
    """Export task details."""

    task_id: str
    source_arn: str
    s3_location: str
    status: ExportStatus
    percent_progress: int
    total_size_gb: float | None = None
    start_time: datetime.datetime | None = None
    end_time: datetime.datetime | None = None
    failure_reason: str | None = None


class S3BackupExporter:
    """Manages RDS snapshot exports to S3."""

    def __init__(self, region: str = "eu-north-1") -> None:
        self.region = region
        self.rds = boto3.client("rds", region_name=region)
        self.s3 = boto3.client("s3", region_name=region)
        self.cloudwatch = boto3.client("cloudwatch", region_name=region)

        # Configuration from environment or defaults
        self.bucket_name = os.environ.get("BACKUP_BUCKET", "babyshield-backup-exports")
        self.kms_key_id = os.environ.get("BACKUP_KMS_KEY", "alias/babyshield-s3-backup")
        self.iam_role_arn = os.environ.get(
            "EXPORT_IAM_ROLE",
            f"arn:aws:iam::{self._get_account_id()}:role/rds-s3-export-role",
        )

    def _get_account_id(self) -> str:
        """Get current AWS account ID."""
        sts = boto3.client("sts")
        return sts.get_caller_identity()["Account"]

    def export_latest_snapshot(
        self,
        db_instance: str = "babyshield-prod",
        tables: list[str] | None = None,
    ) -> str | None:
        """Export the latest automated snapshot to S3."""
        try:
            # Get latest snapshot
            snapshot = self._get_latest_snapshot(db_instance)
            if not snapshot:
                logger.error(f"No snapshot found for {db_instance}")
                return None

            snapshot_id = snapshot["DBSnapshotIdentifier"]
            snapshot_arn = snapshot["DBSnapshotArn"]

            # Generate export task ID
            task_id = f"export-{db_instance}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

            # S3 prefix for organization
            s3_prefix = f"rds-exports/{datetime.datetime.now().strftime('%Y/%m/%d')}/{task_id}/"

            logger.info(f"Starting export of {snapshot_id} to s3://{self.bucket_name}/{s3_prefix}")

            # Start export task
            params = {
                "ExportTaskIdentifier": task_id,
                "SourceArn": snapshot_arn,
                "S3BucketName": self.bucket_name,
                "S3Prefix": s3_prefix,
                "IamRoleArn": self.iam_role_arn,
                "KmsKeyId": self.kms_key_id,
            }

            # Add specific tables if requested
            if tables:
                params["ExportOnly"] = tables
                logger.info(f"Exporting only tables: {tables}")

            response = self.rds.start_export_task(**params)

            logger.info(f"Export task started: {task_id}")
            logger.info(f"Initial status: {response.get('Status')}")

            # Record metric
            self._record_export_started()

            return task_id

        except Exception as e:
            logger.exception(f"Failed to start export: {e}")
            self._record_export_failed()
            return None

    def _get_latest_snapshot(self, db_instance: str) -> dict | None:
        """Get the most recent automated snapshot."""
        try:
            response = self.rds.describe_db_snapshots(
                DBInstanceIdentifier=db_instance,
                SnapshotType="automated",
                MaxRecords=10,
            )

            if not response["DBSnapshots"]:
                return None

            # Sort by creation time
            snapshots = sorted(
                response["DBSnapshots"],
                key=lambda x: x["SnapshotCreateTime"],
                reverse=True,
            )

            return snapshots[0]

        except Exception as e:
            logger.exception(f"Error getting snapshots: {e}")
            return None

    def monitor_export(self, task_id: str) -> ExportTask:
        """Monitor an export task."""
        try:
            response = self.rds.describe_export_tasks(ExportTaskIdentifier=task_id)

            if not response["ExportTasks"]:
                logger.error(f"Export task not found: {task_id}")
                return None

            task = response["ExportTasks"][0]

            # Parse task details
            return ExportTask(
                task_id=task["ExportTaskIdentifier"],
                source_arn=task["SourceArn"],
                s3_location=f"s3://{task['S3Bucket']}/{task['S3Prefix']}",
                status=ExportStatus(task["Status"]),
                percent_progress=task.get("PercentProgress", 0),
                total_size_gb=task.get("TotalExtractedDataInGB"),
                start_time=task.get("TaskStartTime"),
                end_time=task.get("TaskEndTime"),
                failure_reason=task.get("FailureCause"),
            )

        except Exception as e:
            logger.exception(f"Error monitoring export: {e}")
            return None

    def wait_for_export(
        self,
        task_id: str,
        timeout_minutes: int = 120,
        poll_interval: int = 60,
    ) -> tuple[bool, ExportTask]:
        """Wait for export to complete."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        logger.info(f"Waiting for export {task_id} to complete...")

        while (time.time() - start_time) < timeout_seconds:
            task = self.monitor_export(task_id)

            if not task:
                return False, None

            logger.info(f"Export status: {task.status.value} ({task.percent_progress}% complete)")

            if task.status == ExportStatus.COMPLETE:
                logger.info("Export completed successfully!")
                logger.info(f"Location: {task.s3_location}")
                logger.info(f"Size: {task.total_size_gb:.2f} GB")
                self._record_export_success(task)
                return True, task

            if task.status == ExportStatus.FAILED:
                logger.error(f"Export failed: {task.failure_reason}")
                self._record_export_failed()
                return False, task

            if task.status == ExportStatus.CANCELLED:
                logger.warning("Export was cancelled")
                return False, task

            time.sleep(poll_interval)

        logger.error(f"Export timed out after {timeout_minutes} minutes")
        return False, task

    def verify_export(self, task: ExportTask) -> bool:
        """Verify exported files in S3."""
        try:
            # Parse S3 location
            bucket, prefix = task.s3_location.replace("s3://", "").split("/", 1)

            # List objects in export location
            response = self.s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=100)

            if "Contents" not in response:
                logger.error("No files found in export location")
                return False

            files = response["Contents"]
            logger.info(f"Found {len(files)} exported files")

            # Check for expected file patterns
            expected_patterns = ["_metadata.json", ".parquet", "manifest.json"]

            found_patterns = {pattern: False for pattern in expected_patterns}
            total_size = 0

            for file in files:
                key = file["Key"]
                size = file["Size"]
                total_size += size

                for pattern in expected_patterns:
                    if pattern in key:
                        found_patterns[pattern] = True

                logger.debug(f"  - {key} ({size / (1024**2):.2f} MB)")

            # Verify expected files exist
            for pattern, found in found_patterns.items():
                if found:
                    logger.info(f"✅ Found {pattern} files")
                else:
                    logger.warning(f"❌ Missing {pattern} files")

            total_size_gb = total_size / (1024**3)
            logger.info(f"Total export size: {total_size_gb:.2f} GB")

            return all(found_patterns.values())

        except Exception as e:
            logger.exception(f"Error verifying export: {e}")
            return False

    def cleanup_old_exports(self, days_to_keep: int = 30) -> int:
        """Clean up old exports from S3."""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)

            # List all exports
            paginator = self.s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix="rds-exports/")

            objects_to_delete = []

            for page in pages:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    if obj["LastModified"].replace(tzinfo=None) < cutoff_date:
                        objects_to_delete.append({"Key": obj["Key"]})

                        if len(objects_to_delete) >= 1000:
                            # Delete in batches of 1000
                            self._delete_objects(objects_to_delete)
                            objects_to_delete = []

            # Delete remaining objects
            if objects_to_delete:
                self._delete_objects(objects_to_delete)

            total_deleted = len(objects_to_delete)
            logger.info(f"Cleaned up {total_deleted} old export files")

            return total_deleted

        except Exception as e:
            logger.exception(f"Error cleaning up exports: {e}")
            return 0

    def _delete_objects(self, objects: list[dict]) -> None:
        """Delete objects from S3."""
        if not objects:
            return

        try:
            response = self.s3.delete_objects(Bucket=self.bucket_name, Delete={"Objects": objects})

            if "Errors" in response:
                for error in response["Errors"]:
                    logger.error(f"Failed to delete {error['Key']}: {error['Message']}")

        except Exception as e:
            logger.exception(f"Error deleting objects: {e}")

    def get_export_statistics(self) -> dict:
        """Get export statistics."""
        try:
            # Get recent exports
            response = self.rds.describe_export_tasks(MaxRecords=20)

            stats = {
                "total_exports": 0,
                "successful_exports": 0,
                "failed_exports": 0,
                "in_progress": 0,
                "total_size_gb": 0,
                "average_duration_minutes": 0,
                "recent_exports": [],
            }

            durations = []

            for task in response.get("ExportTasks", []):
                stats["total_exports"] += 1

                status = task["Status"]
                if status == "COMPLETE":
                    stats["successful_exports"] += 1
                    stats["total_size_gb"] += task.get("TotalExtractedDataInGB", 0)

                    # Calculate duration
                    if task.get("TaskStartTime") and task.get("TaskEndTime"):
                        duration = (task["TaskEndTime"] - task["TaskStartTime"]).total_seconds() / 60
                        durations.append(duration)

                elif status == "FAILED":
                    stats["failed_exports"] += 1
                elif status in ["STARTING", "IN_PROGRESS"]:
                    stats["in_progress"] += 1

                # Add to recent list
                stats["recent_exports"].append(
                    {
                        "task_id": task["ExportTaskIdentifier"],
                        "status": status,
                        "progress": task.get("PercentProgress", 0),
                        "size_gb": task.get("TotalExtractedDataInGB", 0),
                        "start_time": task.get("TaskStartTime").isoformat() if task.get("TaskStartTime") else None,
                    },
                )

            # Calculate average duration
            if durations:
                stats["average_duration_minutes"] = sum(durations) / len(durations)

            return stats

        except Exception as e:
            logger.exception(f"Error getting statistics: {e}")
            return {}

    def _record_export_started(self) -> None:
        """Record export started metric."""
        try:
            self.cloudwatch.put_metric_data(
                Namespace="BabyShield/Backups",
                MetricData=[
                    {
                        "MetricName": "ExportStarted",
                        "Value": 1,
                        "Unit": "Count",
                        "Timestamp": datetime.datetime.now(datetime.UTC),
                    },
                ],
            )
        except Exception as e:
            logger.exception(f"Error recording metric: {e}")

    def _record_export_success(self, task: ExportTask) -> None:
        """Record successful export metrics."""
        try:
            # Calculate duration
            duration_minutes = 0
            if task.start_time and task.end_time:
                duration_minutes = (task.end_time - task.start_time).total_seconds() / 60

            self.cloudwatch.put_metric_data(
                Namespace="BabyShield/Backups",
                MetricData=[
                    {
                        "MetricName": "ExportSuccess",
                        "Value": 1,
                        "Unit": "Count",
                        "Timestamp": datetime.datetime.now(datetime.UTC),
                    },
                    {
                        "MetricName": "ExportDuration",
                        "Value": duration_minutes,
                        "Unit": "Minutes",
                        "Timestamp": datetime.datetime.now(datetime.UTC),
                    },
                    {
                        "MetricName": "ExportSize",
                        "Value": task.total_size_gb or 0,
                        "Unit": "Gigabytes",
                        "Timestamp": datetime.datetime.now(datetime.UTC),
                    },
                ],
            )
        except Exception as e:
            logger.exception(f"Error recording metrics: {e}")

    def _record_export_failed(self) -> None:
        """Record failed export metric."""
        try:
            self.cloudwatch.put_metric_data(
                Namespace="BabyShield/Backups",
                MetricData=[
                    {
                        "MetricName": "ExportFailed",
                        "Value": 1,
                        "Unit": "Count",
                        "Timestamp": datetime.datetime.now(datetime.UTC),
                    },
                ],
            )
        except Exception as e:
            logger.exception(f"Error recording metric: {e}")


def main() -> int:
    """Main entry point for scheduled exports."""
    logger.info("=" * 60)
    logger.info(" S3 BACKUP EXPORT")
    logger.info(f" Time: {datetime.datetime.now(datetime.UTC).isoformat()}")
    logger.info("=" * 60)

    # Create exporter
    exporter = S3BackupExporter()

    # Get export configuration
    tables_to_export = os.environ.get("EXPORT_TABLES", "").split(",") if os.environ.get("EXPORT_TABLES") else None

    # Start export
    task_id = exporter.export_latest_snapshot(tables=tables_to_export)

    if not task_id:
        logger.error("Failed to start export")
        return 1

    # Wait for completion
    success, task = exporter.wait_for_export(task_id)

    if success:
        # Verify export
        verified = exporter.verify_export(task)

        if verified:
            logger.info("✅ Export completed and verified successfully")
        else:
            logger.warning("⚠️ Export completed but verification failed")

        # Get statistics
        stats = exporter.get_export_statistics()
        logger.info(f"Export statistics: {json.dumps(stats, indent=2, default=str)}")

        # Cleanup old exports (optional)
        if os.environ.get("CLEANUP_OLD_EXPORTS", "true").lower() == "true":
            deleted = exporter.cleanup_old_exports(days_to_keep=30)
            logger.info(f"Cleaned up {deleted} old export files")

        return 0
    logger.error("Export failed or timed out")
    return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
