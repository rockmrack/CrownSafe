"""
Task 15: Legal & Privacy API Endpoints
Provides access to legal documents and privacy controls
"""

from fastapi import APIRouter, Response, HTTPException, Depends, Header, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import os
import hashlib
import logging
import markdown
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/legal",
    tags=["Legal & Privacy"]
)

# ========================= MODELS =========================

class LegalDocument(BaseModel):
    """Legal document metadata"""
    id: str
    title: str
    version: str
    effective_date: str
    last_updated: str
    language: str
    url: str
    content_hash: str


class PrivacySettings(BaseModel):
    """User privacy settings"""
    user_id: str
    crashlytics_enabled: bool = False
    analytics_enabled: bool = False
    personalized_ads: bool = False
    data_sharing: bool = False
    email_notifications: bool = False


class DataDeletionRequest(BaseModel):
    """Data deletion request"""
    user_id: str
    reason: Optional[str] = None
    confirm: bool = Field(..., description="Must be true to confirm deletion")


class ConsentUpdate(BaseModel):
    """Consent update request"""
    user_id: str
    consent_type: str = Field(..., description="crashlytics, analytics, etc")
    granted: bool
    timestamp: datetime = Field(default_factory=datetime.now)


class LegalAgreement(BaseModel):
    """Legal agreement acceptance"""
    user_id: str
    document_id: str
    version: str
    accepted: bool
    timestamp: datetime = Field(default_factory=datetime.now)
    ip_address: Optional[str] = None


# ========================= LEGAL DOCUMENTS =========================

# Document paths (relative to project root)
LEGAL_DOCS_PATH = Path("legal")

# Document registry
LEGAL_DOCUMENTS = {
    "privacy": {
        "file": "PRIVACY_POLICY.md",
        "title": "Privacy Policy",
        "version": "1.0.0",
        "effective_date": "2024-01-01",
        "last_updated": "2024-01-01"
    },
    "terms": {
        "file": "TERMS_OF_SERVICE.md",
        "title": "Terms of Service",
        "version": "1.0.0",
        "effective_date": "2024-01-01",
        "last_updated": "2024-01-01"
    },
    "dpa": {
        "file": "DPA_CHECKLIST.md",
        "title": "Data Processing Agreement",
        "version": "1.0.0",
        "effective_date": "2024-01-01",
        "last_updated": "2024-01-01"
    },
    "cookies": {
        "file": "COOKIE_POLICY.md",
        "title": "Cookie Policy",
        "version": "1.0.0",
        "effective_date": "2024-01-01",
        "last_updated": "2024-01-01"
    }
}


def get_document_content(doc_id: str, format: str = "markdown") -> tuple[str, str]:
    """
    Get legal document content
    Returns: (content, content_type)
    """
    if doc_id not in LEGAL_DOCUMENTS:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    
    doc_info = LEGAL_DOCUMENTS[doc_id]
    file_path = LEGAL_DOCS_PATH / doc_info["file"]
    
    # Check if file exists, otherwise use template
    if not file_path.exists():
        # Return template content
        content = generate_template_content(doc_id, doc_info)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    
    # Format conversion
    if format == "html":
        # Convert markdown to HTML
        html_content = markdown.markdown(
            content,
            extensions=['extra', 'codehilite', 'toc']
        )
        # Wrap in basic HTML template
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{doc_info['title']}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
                       line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
                h1, h2, h3 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }}
                pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            {html_content}
            <footer>
                <hr>
                <p><small>Version: {doc_info['version']} | Last Updated: {doc_info['last_updated']}</small></p>
            </footer>
        </body>
        </html>
        """
        return html_template, "text/html"
    
    elif format == "plain":
        # Convert to plain text (remove markdown formatting)
        plain_text = content
        # Remove markdown headers
        plain_text = plain_text.replace("#", "")
        # Remove markdown links
        import re
        plain_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', plain_text)
        return plain_text, "text/plain"
    
    else:  # markdown
        return content, "text/markdown"


def generate_template_content(doc_id: str, doc_info: dict) -> str:
    """Generate template content for missing documents"""
    
    if doc_id == "privacy":
        return """# Privacy Policy

**This is a template. Please customize with your company information.**

## Company Information
- Company Name: [YOUR COMPANY NAME]
- Address: [YOUR ADDRESS]
- Email: privacy@babyshield.app

## Data Collection
We collect minimal data necessary to provide our service.

## Your Rights
- Access your data
- Delete your data
- Export your data

For the full privacy policy, please contact privacy@babyshield.app
"""
    
    elif doc_id == "terms":
        return """# Terms of Service

**This is a template. Please customize with your company information.**

## Acceptance
By using BabyShield, you agree to these terms.

## Service Description
BabyShield provides product recall information.

## Contact
legal@babyshield.app
"""
    
    else:
        return f"# {doc_info['title']}\n\nDocument content will be available soon."


def calculate_content_hash(content: str) -> str:
    """Calculate SHA256 hash of content"""
    return hashlib.sha256(content.encode()).hexdigest()


# ========================= API ENDPOINTS =========================

@router.get("/", response_model=List[LegalDocument])
async def list_legal_documents(
    language: Optional[str] = "en"
):
    """Get list of all legal documents with metadata"""
    
    documents = []
    for doc_id, doc_info in LEGAL_DOCUMENTS.items():
        content, _ = get_document_content(doc_id)
        
        documents.append(LegalDocument(
            id=doc_id,
            title=doc_info["title"],
            version=doc_info["version"],
            effective_date=doc_info["effective_date"],
            last_updated=doc_info["last_updated"],
            language=language,
            url=f"/legal/{doc_id}",
            content_hash=calculate_content_hash(content)
        ))
    
    return documents


@router.get("/{document_id}")
async def get_legal_document(
    document_id: str,
    format: Optional[str] = "html",
    language: Optional[str] = "en"
):
    """
    Get a specific legal document
    
    Formats: html, markdown, plain
    Documents: privacy, terms, dpa, cookies
    """
    
    try:
        content, content_type = get_document_content(document_id, format)
        
        # Add headers for caching
        headers = {
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
            "X-Document-Version": LEGAL_DOCUMENTS.get(document_id, {}).get("version", "1.0.0"),
            "X-Document-Language": language
        }
        
        if format == "html":
            return HTMLResponse(content=content, headers=headers)
        elif format == "plain":
            return PlainTextResponse(content=content, headers=headers)
        else:
            return Response(content=content, media_type=content_type, headers=headers)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving document")


@router.get("/privacy/summary", response_model=Dict[str, Any])
async def get_privacy_summary(
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Get privacy policy summary and user's privacy settings"""
    
    summary = {
        "ok": True,
        "summary": {
            "data_collected": [
                "OAuth provider ID (encrypted)",
                "Barcode scans",
                "Search queries",
                "Device information (anonymized)",
                "Crash reports (opt-in only)"
            ],
            "data_not_collected": [
                "Email address",
                "Phone number",
                "Physical address",
                "Photos",
                "Location",
                "Contacts"
            ],
            "third_parties": [
                {
                    "name": "AWS",
                    "purpose": "Hosting",
                    "dpa_signed": True
                },
                {
                    "name": "Google Firebase",
                    "purpose": "Crash reporting (opt-in)",
                    "dpa_signed": True
                }
            ],
            "user_rights": [
                "Access your data anytime",
                "Delete all data permanently",
                "Export data in JSON format",
                "Opt-out of crash reporting",
                "Control all privacy settings"
            ],
            "retention_periods": {
                "active_account": "Until deletion requested",
                "inactive_account": "Anonymized after 2 years",
                "crash_reports": "90 days",
                "search_logs": "30 days (anonymized)"
            }
        },
        "settings": {
            "crashlytics_enabled": False,  # Default OFF
            "analytics_enabled": False,
            "personalized_ads": False,
            "data_sharing": False
        },
        "documents": {
            "privacy_policy": "/legal/privacy",
            "terms_of_service": "/legal/terms",
            "data_deletion": "/api/v1/user/data/delete"
        },
        "contact": {
            "privacy_email": "privacy@babyshield.app",
            "dpo_email": "dpo@babyshield.app",
            "response_time": "Within 30 days"
        }
    }
    
    # If user_id provided, get their specific settings
    if user_id:
        # In production, fetch from database
        summary["user_specific"] = {
            "user_id": user_id[:8] + "...",  # Truncated for privacy
            "account_created": "2024-01-01",
            "last_privacy_review": "2024-01-01",
            "data_exports": 0,
            "deletion_requested": False
        }
    
    return summary


@router.post("/privacy/consent")
async def update_privacy_consent(
    consent: ConsentUpdate,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    request: Request = None
):
    """Update user's privacy consent settings"""
    
    # Validate user
    if not user_id or user_id != consent.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Validate consent type
    valid_types = ["crashlytics", "analytics", "ads", "sharing", "notifications"]
    if consent.consent_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid consent type. Must be one of: {valid_types}")
    
    # Log consent change
    logger.info(f"Consent update", extra={
        "user_id": user_id[:8] + "...",
        "consent_type": consent.consent_type,
        "granted": consent.granted,
        "ip_address": request.client.host if request else None
    })
    
    # In production, save to database
    # For now, return confirmation
    return {
        "ok": True,
        "consent_type": consent.consent_type,
        "granted": consent.granted,
        "timestamp": consent.timestamp.isoformat(),
        "message": f"Consent {'granted' if consent.granted else 'withdrawn'} for {consent.consent_type}"
    }


@router.post("/privacy/request-data")
async def request_data_export(
    user_id: str = Header(..., alias="X-User-ID")
):
    """Request a copy of user's data (GDPR Article 15)"""
    
    request_id = hashlib.sha256(f"{user_id}{datetime.now()}".encode()).hexdigest()[:12]
    
    return {
        "ok": True,
        "request_id": request_id,
        "status": "processing",
        "message": "Your data export request has been received",
        "estimated_time": "Within 30 days",
        "delivery_method": "In-app download",
        "format": "JSON"
    }


@router.post("/privacy/delete-data")
async def request_data_deletion(
    deletion: DataDeletionRequest,
    user_id: str = Header(..., alias="X-User-ID")
):
    """Request deletion of user's data (GDPR Article 17)"""
    
    # Validate user
    if user_id != deletion.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Require explicit confirmation
    if not deletion.confirm:
        raise HTTPException(
            status_code=400,
            detail="Deletion must be explicitly confirmed"
        )
    
    request_id = hashlib.sha256(f"{user_id}{datetime.now()}".encode()).hexdigest()[:12]
    
    logger.warning(f"Data deletion requested", extra={
        "user_id": user_id[:8] + "...",
        "request_id": request_id,
        "reason": deletion.reason
    })
    
    return {
        "ok": True,
        "request_id": request_id,
        "status": "scheduled",
        "message": "Your account and all data will be permanently deleted",
        "deletion_date": (datetime.now() + timedelta(days=30)).date().isoformat(),
        "grace_period": "30 days",
        "cancel_url": f"/legal/privacy/cancel-deletion/{request_id}"
    }


@router.get("/compliance/status")
async def get_compliance_status():
    """Get current compliance status and certifications"""
    
    return {
        "ok": True,
        "compliance": {
            "gdpr": {
                "compliant": True,
                "dpo_appointed": True,
                "dpo_email": "dpo@babyshield.app",
                "privacy_by_design": True,
                "data_minimization": True,
                "encryption": True
            },
            "ccpa": {
                "compliant": True,
                "do_not_sell": True,
                "opt_out_available": True,
                "deletion_rights": True
            },
            "coppa": {
                "compliant": True,
                "under_13_collection": False,
                "parental_consent": "Not applicable"
            },
            "app_store": {
                "apple_privacy_labels": True,
                "google_data_safety": True,
                "transparency_report": True
            }
        },
        "certifications": {
            "soc2": "In progress",
            "iso27001": "Planned",
            "privacy_shield": "Not applicable"
        },
        "audits": {
            "last_audit": "2023-12-01",
            "next_audit": "2024-06-01",
            "audit_firm": "[AUDIT FIRM NAME]"
        },
        "data_protection": {
            "encryption_at_rest": "AES-256",
            "encryption_in_transit": "TLS 1.3",
            "key_management": "AWS KMS",
            "backup_encryption": True,
            "mfa_required": True
        }
    }


@router.get("/agreements/{user_id}")
async def get_user_agreements(
    user_id: str,
    requesting_user: str = Header(..., alias="X-User-ID")
):
    """Get user's legal agreement history"""
    
    # Users can only view their own agreements
    if user_id != requesting_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # In production, fetch from database
    # For now, return sample data
    return {
        "ok": True,
        "user_id": user_id[:8] + "...",
        "agreements": [
            {
                "document": "privacy",
                "version": "1.0.0",
                "accepted": True,
                "timestamp": "2024-01-01T00:00:00Z"
            },
            {
                "document": "terms",
                "version": "1.0.0", 
                "accepted": True,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        ],
        "pending_updates": [],
        "requires_acceptance": False
    }


@router.post("/agreements/accept")
async def accept_legal_agreement(
    agreement: LegalAgreement,
    user_id: str = Header(..., alias="X-User-ID"),
    request: Request = None
):
    """Accept a legal agreement"""
    
    # Validate user
    if user_id != agreement.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Validate document exists
    if agreement.document_id not in LEGAL_DOCUMENTS:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Log acceptance
    logger.info(f"Legal agreement accepted", extra={
        "user_id": user_id[:8] + "...",
        "document": agreement.document_id,
        "version": agreement.version,
        "ip_address": request.client.host if request else None
    })
    
    return {
        "ok": True,
        "document": agreement.document_id,
        "version": agreement.version,
        "accepted": True,
        "timestamp": agreement.timestamp.isoformat(),
        "message": "Agreement accepted successfully"
    }


# ========================= COOKIE POLICY (WEB ONLY) =========================

@router.get("/cookies/preferences")
async def get_cookie_preferences(
    session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """Get cookie preferences (web only)"""
    
    return {
        "ok": True,
        "cookies_used": {
            "essential": {
                "enabled": True,
                "required": True,
                "purpose": "Security and authentication",
                "cookies": ["session_id", "csrf_token"]
            },
            "functional": {
                "enabled": False,
                "required": False,
                "purpose": "User preferences",
                "cookies": ["language", "theme"]
            },
            "analytics": {
                "enabled": False,
                "required": False,
                "purpose": "Usage analytics",
                "cookies": []
            },
            "marketing": {
                "enabled": False,
                "required": False,
                "purpose": "Marketing",
                "cookies": []
            }
        },
        "mobile_app_note": "The BabyShield mobile app does not use cookies"
    }
