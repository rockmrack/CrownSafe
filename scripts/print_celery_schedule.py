#!/usr/bin/env python3
"""Sanity check script to print Celery Beat schedule configuration."""

from core_infra.risk_ingestion_tasks import celery_app

s = celery_app.conf.beat_schedule or {}
print({k: s[k]["task"] for k in s})
