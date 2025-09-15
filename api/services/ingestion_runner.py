"""
Ingestion runner service for executing data ingestion jobs
Manages subprocess execution and status tracking
"""

import os
import sys
import asyncio
import shlex
import re
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

from sqlalchemy import insert, update, select
from sqlalchemy.orm import Session
from core_infra.database import get_db_session, engine
from models.ingestion_run import IngestionRun

logger = logging.getLogger(__name__)

# Configuration
PYTHON_BIN = os.getenv("PYTHON_BIN", sys.executable)
APP_ROOT = Path(os.getenv("APP_ROOT", os.getcwd()))
INGESTION_TIMEOUT = int(os.getenv("INGESTION_TIMEOUT", "3600"))  # 1 hour default


class IngestionRunner:
    """
    Service for running ingestion jobs
    """
    
    # Supported agencies
    SUPPORTED_AGENCIES = {
        "FDA", "EU_RAPEX", "EU_SAFETY_GATE", "CPSC", "NHTSA", 
        "USDA", "EPA", "CDC", "FSIS", "UK_OPSS", 
        "HEALTH_CANADA", "AUSTRALIA_ACCC", "JAPAN_CAA"
    }
    
    # Running jobs tracker (in-memory for now)
    _running_jobs: Dict[str, asyncio.Task] = {}
    
    @classmethod
    def _get_timestamp(cls) -> datetime:
        """Get current UTC timestamp"""
        return datetime.utcnow().replace(tzinfo=timezone.utc)
    
    @classmethod
    async def _execute_command(
        cls,
        cmd: str,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Tuple[int, str, str]:
        """
        Execute a shell command asynchronously
        
        Args:
            cmd: Command to execute
            env: Environment variables
            timeout: Timeout in seconds
        
        Returns:
            (return_code, stdout, stderr)
        """
        logger.info(f"Executing command: {cmd}")
        
        # Merge environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        try:
            # Create subprocess
            proc = await asyncio.create_subprocess_shell(
                cmd,
                env=process_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(APP_ROOT)
            )
            
            # Wait with timeout
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout or INGESTION_TIMEOUT
            )
            
            return_code = proc.returncode or 0
            stdout_str = stdout.decode(errors="ignore") if stdout else ""
            stderr_str = stderr.decode(errors="ignore") if stderr else ""
            
            logger.debug(f"Command completed with code {return_code}")
            
            return return_code, stdout_str, stderr_str
            
        except asyncio.TimeoutError:
            logger.error(f"Command timed out after {timeout}s")
            if proc:
                proc.terminate()
                await asyncio.sleep(0.5)
                if proc.returncode is None:
                    proc.kill()
            return -1, "", f"Command timed out after {timeout} seconds"
        
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return -1, "", str(e)
    
    @classmethod
    def _parse_output(cls, stdout: str, stderr: str) -> Dict[str, int]:
        """
        Parse ingestion script output for metrics
        
        Args:
            stdout: Standard output
            stderr: Standard error
        
        Returns:
            Dictionary with metrics
        """
        metrics = {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0
        }
        
        # Combined output
        output = stdout + "\n" + stderr
        
        # Pattern matching for common output formats
        patterns = [
            (r"Inserted[:\s]+(\d+)", "inserted"),
            (r"(\d+)\s+records?\s+inserted", "inserted"),
            (r"Updated[:\s]+(\d+)", "updated"),
            (r"(\d+)\s+records?\s+updated", "updated"),
            (r"Skipped[:\s]+(\d+)", "skipped"),
            (r"(\d+)\s+records?\s+skipped", "skipped"),
            (r"Failed[:\s]+(\d+)", "failed"),
            (r"(\d+)\s+errors?", "failed"),
            (r"Total[:\s]+(\d+)\s+new", "inserted"),
            (r"Processed[:\s]+(\d+)", "updated"),
        ]
        
        for pattern, metric_name in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                metrics[metric_name] = max(metrics[metric_name], int(match.group(1)))
        
        # Try to parse JSON output if present
        json_match = re.search(r'\{[^}]*"inserted"[^}]*\}', output)
        if json_match:
            try:
                json_data = json.loads(json_match.group(0))
                for key in metrics:
                    if key in json_data:
                        metrics[key] = json_data[key]
            except json.JSONDecodeError:
                pass
        
        logger.debug(f"Parsed metrics: {metrics}")
        return metrics
    
    @classmethod
    def _build_command(cls, agency: str, mode: str) -> str:
        """
        Build ingestion command for agency and mode
        
        Args:
            agency: Agency code
            mode: Ingestion mode (delta, full, incremental)
        
        Returns:
            Shell command string
        """
        agency = agency.upper()
        
        # Map agency names
        if agency == "EU_SAFETY_GATE":
            agency = "EU_RAPEX"
        
        # Check if we have a specific script for this agency
        script_path = APP_ROOT / "scripts" / "ingest_recalls.py"
        
        if script_path.exists():
            # Use the main ingestion script
            cmd = f'"{PYTHON_BIN}" "{script_path}" --agencies {shlex.quote(agency)}'
            
            if mode == "delta":
                # Delta mode - last 30 days
                from datetime import timedelta
                since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                cmd += f" --since {since}"
            elif mode == "full":
                # Full mode - all data
                cmd += " --since 1900-01-01"
            # incremental uses default behavior
            
        else:
            # Fallback to module execution
            cmd = f'"{PYTHON_BIN}" -m scripts.ingest_recalls --agencies {shlex.quote(agency)}'
            
            if mode == "delta":
                cmd += " --since 2024-01-01"
        
        logger.info(f"Built command for {agency}/{mode}: {cmd}")
        return cmd
    
    @classmethod
    async def start_ingestion(
        cls,
        agency: str,
        mode: str,
        trace_id: Optional[str] = None,
        initiated_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, str, str]:
        """
        Start an ingestion job
        
        Args:
            agency: Agency to ingest from
            mode: Ingestion mode (delta, full, incremental)
            trace_id: Request trace ID
            initiated_by: Who initiated the job
            metadata: Additional metadata to store
        
        Returns:
            (run_id, status, stdout, stderr)
        """
        agency = agency.upper()
        mode = mode.lower()
        
        # Validate inputs
        if agency not in cls.SUPPORTED_AGENCIES:
            raise ValueError(f"Unsupported agency: {agency}")
        
        if mode not in ("delta", "full", "incremental"):
            raise ValueError(f"Invalid mode: {mode}")
        
        # Check if already running for this agency
        running_key = f"{agency}_{mode}"
        if running_key in cls._running_jobs:
            task = cls._running_jobs[running_key]
            if not task.done():
                logger.warning(f"Ingestion already running for {agency}/{mode}")
                return "", "already_running", "", "Ingestion already in progress"
        
        # Create ingestion run record
        with get_db_session() as db:
            run = IngestionRun(
                agency=agency,
                mode=mode,
                status="queued",
                initiated_by=initiated_by,
                trace_id=trace_id,
                metadata_json=metadata
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            run_id = str(run.id)
        
        # Build command
        cmd = cls._build_command(agency, mode)
        
        # Create async task for execution
        task = asyncio.create_task(
            cls._execute_ingestion(run_id, cmd, running_key)
        )
        cls._running_jobs[running_key] = task
        
        logger.info(f"Started ingestion {run_id} for {agency}/{mode}")
        
        return run_id, "queued", "", ""
    
    @classmethod
    async def _execute_ingestion(cls, run_id: str, cmd: str, running_key: str):
        """
        Execute ingestion in background
        
        Args:
            run_id: Ingestion run ID
            cmd: Command to execute
            running_key: Key for tracking running jobs
        """
        try:
            # Update status to running
            with get_db_session() as db:
                db.execute(
                    update(IngestionRun)
                    .where(IngestionRun.id == run_id)
                    .values(
                        status="running",
                        started_at=cls._get_timestamp()
                    )
                )
                db.commit()
            
            # Execute command
            return_code, stdout, stderr = await cls._execute_command(
                cmd,
                env={"PYTHONUNBUFFERED": "1"}  # Ensure unbuffered output
            )
            
            # Parse metrics
            metrics = cls._parse_output(stdout, stderr)
            
            # Determine status
            if return_code == 0:
                status = "success"
                error_text = None
            else:
                status = "failed"
                error_text = stderr[-5000:] if stderr else f"Exit code: {return_code}"
            
            # Update run record
            with get_db_session() as db:
                db.execute(
                    update(IngestionRun)
                    .where(IngestionRun.id == run_id)
                    .values(
                        status=status,
                        finished_at=cls._get_timestamp(),
                        items_inserted=metrics["inserted"],
                        items_updated=metrics["updated"],
                        items_skipped=metrics["skipped"],
                        items_failed=metrics["failed"],
                        error_text=error_text
                    )
                )
                db.commit()
            
            logger.info(f"Ingestion {run_id} completed: {status}")
            
        except Exception as e:
            logger.error(f"Ingestion {run_id} error: {e}")
            
            # Mark as failed
            with get_db_session() as db:
                db.execute(
                    update(IngestionRun)
                    .where(IngestionRun.id == run_id)
                    .values(
                        status="failed",
                        finished_at=cls._get_timestamp(),
                        error_text=str(e)[:5000]
                    )
                )
                db.commit()
        
        finally:
            # Remove from running jobs
            if running_key in cls._running_jobs:
                del cls._running_jobs[running_key]
    
    @classmethod
    async def cancel_ingestion(cls, run_id: str) -> bool:
        """
        Cancel a running ingestion
        
        Args:
            run_id: Ingestion run ID
        
        Returns:
            True if cancelled, False otherwise
        """
        # Find the task
        for key, task in cls._running_jobs.items():
            if not task.done():
                # Check if this is our run
                # (Would need to track run_id -> task mapping for this)
                task.cancel()
                
                # Update status
                with get_db_session() as db:
                    db.execute(
                        update(IngestionRun)
                        .where(IngestionRun.id == run_id)
                        .values(
                            status="cancelled",
                            finished_at=cls._get_timestamp(),
                            error_text="Cancelled by user"
                        )
                    )
                    db.commit()
                
                return True
        
        return False
    
    @classmethod
    def get_running_jobs(cls) -> Dict[str, bool]:
        """
        Get currently running jobs
        
        Returns:
            Dictionary of job keys and their running status
        """
        return {
            key: not task.done()
            for key, task in cls._running_jobs.items()
        }


# Export
__all__ = ["IngestionRunner"]
