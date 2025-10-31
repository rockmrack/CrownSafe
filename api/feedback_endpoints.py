"""
In-App Feedback API Endpoints
Handles user feedback submission and routing to support mailbox
"""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from email.message import EmailMessage
from enum import Enum
from typing import List, Optional

import aiosmtplib
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, validator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Router setup
router = APIRouter(prefix="/api/v1/feedback", tags=["feedback", "support"])

# =====================================================
# Configuration
# =====================================================

SMTP_CONFIG = {
    "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
    "port": int(os.environ.get("SMTP_PORT", "587")),
    "username": os.environ.get("SMTP_USERNAME", "support@babyshield.app"),
    "password": os.environ.get("SMTP_PASSWORD", ""),
    "use_tls": True,
}

SUPPORT_CONFIG = {
    "mailbox": os.environ.get("SUPPORT_MAILBOX", "support@babyshield.app"),
    "escalation": os.environ.get("ESCALATION_EMAIL", "escalation@babyshield.app"),
    "security": os.environ.get("SECURITY_EMAIL", "security@babyshield.app"),
    "auto_reply": True,
    "track_metrics": True,
}

# =====================================================
# Models
# =====================================================


class FeedbackType(str, Enum):
    """Types of feedback"""

    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    GENERAL_FEEDBACK = "general_feedback"
    COMPLAINT = "complaint"
    COMPLIMENT = "compliment"
    DATA_ISSUE = "data_issue"
    SECURITY_ISSUE = "security_issue"
    ACCOUNT_ISSUE = "account_issue"
    PAYMENT_ISSUE = "payment_issue"
    OTHER = "other"


class Priority(str, Enum):
    """Ticket priority levels"""

    P0_CRITICAL = "P0"  # System down, security issue
    P1_HIGH = "P1"  # Major functionality broken
    P2_MEDIUM = "P2"  # Minor functionality issue
    P3_LOW = "P3"  # Enhancement or question


class FeedbackRequest(BaseModel):
    """User feedback submission"""

    type: FeedbackType = Field(..., description="Type of feedback")
    subject: str = Field(..., min_length=3, max_length=200, description="Brief subject")
    message: str = Field(..., min_length=10, max_length=5000, description="Detailed message")

    # Optional user info
    user_email: Optional[EmailStr] = Field(None, description="User's email for response")
    user_name: Optional[str] = Field(None, max_length=100, description="User's name")
    user_id: Optional[str] = Field(None, description="Authenticated user ID")

    # App context
    app_version: Optional[str] = Field(None, description="App version")
    device_info: Optional[str] = Field(None, description="Device model and OS")

    # Additional data
    screenshot: Optional[str] = Field(None, description="Base64 encoded screenshot")
    logs: Optional[str] = Field(None, description="App logs if applicable")
    reproduction_steps: Optional[List[str]] = Field(None, description="Steps to reproduce issue")

    # Metadata
    locale: Optional[str] = Field("en-US", description="User's locale")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)

    @validator("message")
    def clean_message(cls, v):
        """Clean and validate message"""
        # Remove excessive whitespace
        v = " ".join(v.split())
        # Check for spam patterns (basic)
        spam_patterns = ["viagra", "cialis", "lottery", "inheritance"]
        if any(pattern in v.lower() for pattern in spam_patterns):
            raise ValueError("Message contains inappropriate content")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "type": "bug_report",
                "subject": "Search not working",
                "message": "When I search for 'Graco car seat', no results appear even though I know there was a recall.",
                "user_email": "user@example.com",
                "user_name": "Jane Doe",
                "app_version": "1.0.0",
                "device_info": "iPhone 14, iOS 17.2",
            }
        }


class FeedbackResponse(BaseModel):
    """Response after feedback submission"""

    ticket_id: str = Field(..., description="Unique ticket identifier")
    ticket_number: int = Field(..., description="Human-readable ticket number")
    status: str = Field(..., description="Ticket status")
    priority: Priority = Field(..., description="Assigned priority")
    estimated_response: str = Field(..., description="Expected response time")
    message: str = Field(..., description="Confirmation message")
    tracking_url: Optional[str] = Field(None, description="URL to track ticket status")


class TicketStatus(BaseModel):
    """Ticket status information"""

    ticket_id: str
    ticket_number: int
    status: str
    priority: Priority
    created_at: datetime
    last_updated: datetime
    assigned_to: Optional[str]
    resolution: Optional[str]
    customer_satisfied: Optional[bool]


# =====================================================
# Support Functions
# =====================================================


def determine_priority(feedback: FeedbackRequest) -> Priority:
    """Determine ticket priority based on feedback content"""

    # P0 - Critical issues
    if feedback.type == FeedbackType.SECURITY_ISSUE:
        return Priority.P0_CRITICAL

    critical_keywords = ["crash", "not working", "down", "error", "broken", "urgent"]
    if any(keyword in feedback.message.lower() for keyword in critical_keywords):
        if feedback.type == FeedbackType.BUG_REPORT:
            return Priority.P1_HIGH

    # P1 - High priority
    if feedback.type in [FeedbackType.DATA_ISSUE, FeedbackType.PAYMENT_ISSUE]:
        return Priority.P1_HIGH

    high_keywords = ["incorrect", "wrong", "missing", "failed"]
    if any(keyword in feedback.message.lower() for keyword in high_keywords):
        return Priority.P1_HIGH

    # P2 - Medium priority
    if feedback.type in [FeedbackType.BUG_REPORT, FeedbackType.ACCOUNT_ISSUE]:
        return Priority.P2_MEDIUM

    # P3 - Low priority
    if feedback.type in [
        FeedbackType.FEATURE_REQUEST,
        FeedbackType.GENERAL_FEEDBACK,
        FeedbackType.COMPLIMENT,
    ]:
        return Priority.P3_LOW

    # Default
    return Priority.P2_MEDIUM


def get_response_time(priority: Priority) -> str:
    """Get expected response time based on priority"""

    response_times = {
        Priority.P0_CRITICAL: "within 1 hour",
        Priority.P1_HIGH: "within 2 hours",
        Priority.P2_MEDIUM: "within 4 hours",
        Priority.P3_LOW: "within 8 hours",
    }

    return response_times.get(priority, "within 24 hours")


def generate_ticket_id() -> tuple[str, int]:
    """Generate unique ticket ID and number"""

    # Generate unique ID
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"

    # Generate ticket number (would be from database in production)
    import random

    ticket_number = random.randint(100000, 999999)

    return ticket_id, ticket_number


async def send_email_notification(
    feedback: FeedbackRequest, ticket_id: str, ticket_number: int, priority: Priority
) -> bool:
    """Send email notification to support mailbox"""

    try:
        # Determine recipient based on priority/type
        if priority == Priority.P0_CRITICAL:
            recipient = SUPPORT_CONFIG["escalation"]
        elif feedback.type == FeedbackType.SECURITY_ISSUE:
            recipient = SUPPORT_CONFIG["security"]
        else:
            recipient = SUPPORT_CONFIG["mailbox"]

        # Create email message
        message = EmailMessage()
        message["From"] = SMTP_CONFIG["username"]
        message["To"] = recipient
        message["Subject"] = f"[{priority}] Ticket #{ticket_number}: {feedback.subject}"

        # Email body
        body = f"""
New Support Ticket Received
============================

Ticket ID: {ticket_id}
Ticket Number: #{ticket_number}
Priority: {priority}
Type: {feedback.type.value}

Customer Information:
--------------------
Name: {feedback.user_name or "Not provided"}
Email: {feedback.user_email or "Not provided"}
User ID: {feedback.user_id or "Anonymous"}

Feedback Details:
----------------
Subject: {feedback.subject}

Message:
{feedback.message}

App Context:
-----------
Version: {feedback.app_version or "Unknown"}
Device: {feedback.device_info or "Unknown"}
Locale: {feedback.locale}
Timestamp: {feedback.timestamp}

{f"Reproduction Steps:{chr(10)}{chr(10).join(f'{i + 1}. {step}' for i, step in enumerate(feedback.reproduction_steps))}" if feedback.reproduction_steps else ""}

Response Time: {get_response_time(priority)}

---
This is an automated notification from BabyShield Support System
        """

        message.set_content(body)

        # Add attachments if present
        if feedback.screenshot:
            # Decode base64 screenshot and attach
            import base64

            try:
                screenshot_data = base64.b64decode(feedback.screenshot)
                message.add_attachment(
                    screenshot_data,
                    maintype="image",
                    subtype="png",
                    filename=f"screenshot_{ticket_number}.png",
                )
            except:
                logger.warning(f"Failed to attach screenshot for ticket {ticket_id}")

        if feedback.logs:
            message.add_attachment(
                feedback.logs.encode("utf-8"),
                maintype="text",
                subtype="plain",
                filename=f"logs_{ticket_number}.txt",
            )

        # Send email asynchronously
        await aiosmtplib.send(
            message,
            hostname=SMTP_CONFIG["host"],
            port=SMTP_CONFIG["port"],
            username=SMTP_CONFIG["username"],
            password=SMTP_CONFIG["password"],
            start_tls=SMTP_CONFIG["use_tls"],
        )

        logger.info(f"Email notification sent for ticket {ticket_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        return False


async def send_auto_reply(
    user_email: str,
    user_name: str,
    ticket_number: int,
    priority: Priority,
    subject: str,
) -> bool:
    """Send automatic reply to user"""

    if not user_email or not SUPPORT_CONFIG["auto_reply"]:
        return False

    try:
        message = EmailMessage()
        message["From"] = SMTP_CONFIG["username"]
        message["To"] = user_email
        message["Subject"] = f"Re: {subject} - Ticket #{ticket_number}"

        response_time = get_response_time(priority)

        body = f"""
Hi {user_name or "there"},

Thank you for contacting BabyShield Support. We've received your message and assigned it ticket #{ticket_number}.

Priority: {priority}
Expected Response: {response_time}

We'll investigate and get back to you shortly.

Track your ticket: https://support.babyshield.app/ticket/{ticket_number}

Best regards,
BabyShield Support Team

---
This is an automated response. Please do not reply to this email.
For urgent issues, call 1-800-BABY-SAFE.
        """

        message.set_content(body)

        # Send email
        await aiosmtplib.send(
            message,
            hostname=SMTP_CONFIG["host"],
            port=SMTP_CONFIG["port"],
            username=SMTP_CONFIG["username"],
            password=SMTP_CONFIG["password"],
            start_tls=SMTP_CONFIG["use_tls"],
        )

        logger.info(f"Auto-reply sent to {user_email} for ticket #{ticket_number}")
        return True

    except Exception as e:
        logger.error(f"Failed to send auto-reply: {e}")
        return False


def track_feedback_metrics(feedback: FeedbackRequest, priority: Priority):
    """Track feedback metrics for analytics"""

    if not SUPPORT_CONFIG["track_metrics"]:
        return

    try:
        # In production, this would send to analytics service
        metrics = {
            "event": "feedback_submitted",
            "type": feedback.type.value,
            "priority": priority.value,
            "has_email": bool(feedback.user_email),
            "has_screenshot": bool(feedback.screenshot),
            "app_version": feedback.app_version,
            "locale": feedback.locale,
            "timestamp": feedback.timestamp.isoformat(),
        }

        logger.info(f"Feedback metrics: {json.dumps(metrics)}")

    except Exception as e:
        logger.error(f"Failed to track metrics: {e}")


# =====================================================
# API Endpoints
# =====================================================


@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest, background_tasks: BackgroundTasks, request: Request):
    """
    Submit user feedback

    Creates a support ticket and sends notification to support team.
    """

    try:
        # Generate ticket details
        ticket_id, ticket_number = generate_ticket_id()
        priority = determine_priority(feedback)
        response_time = get_response_time(priority)

        # Add IP address for security tracking
        client_ip = request.client.host
        logger.info(f"Feedback submitted from IP: {client_ip}")

        # Send email notification to support team
        background_tasks.add_task(send_email_notification, feedback, ticket_id, ticket_number, priority)

        # Send auto-reply to user if email provided
        if feedback.user_email:
            background_tasks.add_task(
                send_auto_reply,
                feedback.user_email,
                feedback.user_name,
                ticket_number,
                priority,
                feedback.subject,
            )

        # Track metrics
        background_tasks.add_task(track_feedback_metrics, feedback, priority)

        # Store ticket in database (mock for now)
        # In production, this would save to database - Reserved for DB implementation
        _ = {
            "ticket_id": ticket_id,
            "ticket_number": ticket_number,
            "priority": priority,
            "status": "open",
            "feedback": feedback.dict(),
            "created_at": datetime.utcnow(),
            "ip_address": client_ip,
        }

        logger.info(f"Ticket created: {ticket_id} (#{ticket_number})")

        # Return response
        return FeedbackResponse(
            ticket_id=ticket_id,
            ticket_number=ticket_number,
            status="open",
            priority=priority,
            estimated_response=response_time,
            message=f"Thank you for your feedback. We'll respond {response_time}.",
            tracking_url=f"https://support.babyshield.app/ticket/{ticket_number}",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback. Please try again.")


@router.get("/ticket/{ticket_number}", response_model=TicketStatus)
async def get_ticket_status(ticket_number: int):
    """
    Get ticket status

    Check the status of a submitted feedback ticket.
    """

    # In production, this would query the database
    # Mock response for now

    return TicketStatus(
        ticket_id=f"TKT-{hashlib.md5(str(ticket_number).encode()).hexdigest()[:8].upper()}",
        ticket_number=ticket_number,
        status="in_progress",
        priority=Priority.P2_MEDIUM,
        created_at=datetime.utcnow(),
        last_updated=datetime.utcnow(),
        assigned_to="Support Agent",
        resolution=None,
        customer_satisfied=None,
    )


@router.post("/ticket/{ticket_number}/satisfy")
async def mark_satisfaction(ticket_number: int, satisfied: bool = True, comments: Optional[str] = None):
    """
    Mark customer satisfaction

    Allow customers to indicate if their issue was resolved satisfactorily.
    """

    # In production, update database

    return {
        "message": "Thank you for your feedback",
        "ticket_number": ticket_number,
        "satisfied": satisfied,
        "comments": comments,
    }


@router.get("/categories")
async def get_feedback_categories():
    """
    Get available feedback categories

    Returns list of feedback types and their descriptions.
    """

    categories = [
        {
            "type": "bug_report",
            "label": "Report a Bug",
            "description": "Something isn't working correctly",
            "icon": "🐛",
        },
        {
            "type": "feature_request",
            "label": "Request a Feature",
            "description": "Suggest a new feature or improvement",
            "icon": "💡",
        },
        {
            "type": "data_issue",
            "label": "Report Data Issue",
            "description": "Incorrect or missing recall information",
            "icon": "⚠️",
        },
        {
            "type": "account_issue",
            "label": "Account Help",
            "description": "Sign-in, subscription, or account issues",
            "icon": "👤",
        },
        {
            "type": "general_feedback",
            "label": "General Feedback",
            "description": "Share your thoughts about BabyShield",
            "icon": "💬",
        },
        {
            "type": "security_issue",
            "label": "Security Concern",
            "description": "Report a security or privacy issue",
            "icon": "🔒",
        },
    ]

    return {"categories": categories}


@router.get("/health")
async def health_check():
    """Health check for feedback service"""

    # Check SMTP connection
    smtp_ok = bool(SMTP_CONFIG["password"])

    return {
        "status": "healthy" if smtp_ok else "degraded",
        "smtp_configured": smtp_ok,
        "auto_reply_enabled": SUPPORT_CONFIG["auto_reply"],
        "metrics_enabled": SUPPORT_CONFIG["track_metrics"],
    }


# =====================================================
# Admin Endpoints (Protected in production)
# =====================================================


@router.get("/admin/stats")
async def get_support_stats():
    """
    Get support statistics

    Returns metrics about feedback submissions (admin only).
    """

    # In production, this would query real data
    # Mock data for demonstration

    return {
        "total_tickets": 1234,
        "open_tickets": 47,
        "avg_response_time": "2.3 hours",
        "satisfaction_rate": 0.94,
        "tickets_by_type": {
            "bug_report": 450,
            "feature_request": 320,
            "data_issue": 180,
            "account_issue": 150,
            "general_feedback": 100,
            "security_issue": 34,
        },
        "tickets_by_priority": {"P0": 5, "P1": 42, "P2": 387, "P3": 800},
    }


@router.post("/admin/bulk_update")
async def bulk_update_tickets(
    ticket_ids: List[str],
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    priority: Optional[Priority] = None,
):
    """
    Bulk update tickets

    Update multiple tickets at once (admin only).
    """

    updates = {}
    if status:
        updates["status"] = status
    if assigned_to:
        updates["assigned_to"] = assigned_to
    if priority:
        updates["priority"] = priority

    # In production, update database

    return {"updated": len(ticket_ids), "ticket_ids": ticket_ids, "updates": updates}


# =====================================================
# Error Handlers
# =====================================================


# Note: Exception handlers should be added at the app level, not router level
# This function is kept for reference but not used as exception handler
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors - should be added at app level"""
    return {"error": "validation_error", "detail": str(exc)}
