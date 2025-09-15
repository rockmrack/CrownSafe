"""
Simplified BabyShield API for testing core functionality
Bypasses optional dependencies that aren't installed
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="BabyShield API (Simplified)",
    version="1.0.0-test",
    description="Simplified version for testing core functionality"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Models ====================

class SafetyCheckRequest(BaseModel):
    user_id: int
    product: str
    product_type: Optional[str] = "general"
    check_pregnancy: Optional[bool] = False
    pregnancy_trimester: Optional[int] = None
    check_allergies: Optional[bool] = False
    allergies: Optional[List[str]] = []

class SafetyCheckResponse(BaseModel):
    status: str
    safety_level: str
    summary: str
    warnings: List[str] = []
    recommendations: List[str] = []
    alternatives: Optional[List[Dict[str, Any]]] = []
    pregnancy_alerts: Optional[List[str]] = []
    allergy_alerts: Optional[List[str]] = []
    timestamp: str

class MobileScanRequest(BaseModel):
    barcode: str
    user_id: int
    scan_type: Optional[str] = "upc"
    check_pregnancy: Optional[bool] = False
    check_allergies: Optional[bool] = False

class MobileScanResponse(BaseModel):
    status: str
    safety_level: str
    product_name: Optional[str] = None
    summary: str
    recalls: List[Dict[str, Any]] = []
    warnings: List[str] = []
    pregnancy_safe: Optional[bool] = None
    allergy_safe: Optional[bool] = None
    response_time_ms: int

class SearchAdvancedRequest(BaseModel):
    product: str
    agencies: Optional[List[str]] = ["FDA", "CPSC", "Health Canada"]
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: Optional[int] = 10

class SearchAdvancedResponse(BaseModel):
    total: int
    agencies: int
    recalls: List[Dict[str, Any]]
    cached: bool = False

# ==================== Endpoints ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "BabyShield API (Simplified)",
        "version": "1.0.0-test",
        "status": "running",
        "message": "Testing mode - limited functionality"
    }

@app.post("/api/v1/safety-check", response_model=SafetyCheckResponse)
async def safety_check(request: SafetyCheckRequest):
    """Perform a safety check on a product"""
    logger.info(f"Safety check for product: {request.product}")
    
    # Simulate safety check
    safety_level = "SAFE"
    warnings = []
    recommendations = ["Always follow manufacturer's instructions"]
    
    if "formula" in request.product.lower():
        recommendations.append("Check expiration date before use")
    
    if request.check_pregnancy and request.pregnancy_trimester:
        if request.pregnancy_trimester == 1:
            warnings.append("First trimester - consult your doctor")
            safety_level = "CAUTION"
    
    if request.check_allergies and request.allergies:
        for allergy in request.allergies:
            if allergy.lower() in request.product.lower():
                warnings.append(f"Contains {allergy}")
                safety_level = "WARNING"
    
    return SafetyCheckResponse(
        status="success",
        safety_level=safety_level,
        summary=f"Safety check completed for {request.product}",
        warnings=warnings,
        recommendations=recommendations,
        alternatives=[],
        pregnancy_alerts=["Consult healthcare provider"] if request.check_pregnancy else [],
        allergy_alerts=[f"Check for {a}" for a in request.allergies] if request.check_allergies else [],
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/v1/mobile/scan", response_model=MobileScanResponse)
async def mobile_scan(request: MobileScanRequest):
    """Process a barcode scan from mobile app"""
    logger.info(f"Mobile scan for barcode: {request.barcode}")
    
    # Simulate barcode lookup
    product_name = f"Product {request.barcode}"
    
    if request.barcode == "123456789012":
        product_name = "Baby Formula Test Product"
    
    return MobileScanResponse(
        status="success",
        safety_level="SAFE",
        product_name=product_name,
        summary=f"No recalls found for {product_name}",
        recalls=[],
        warnings=[],
        pregnancy_safe=True if request.check_pregnancy else None,
        allergy_safe=True if request.check_allergies else None,
        response_time_ms=50
    )

@app.post("/api/v1/search/advanced", response_model=SearchAdvancedResponse)
async def search_advanced(request: SearchAdvancedRequest):
    """Advanced search for product recalls"""
    logger.info(f"Advanced search for: {request.product}")
    
    # Simulate search results
    mock_recalls = []
    
    if "baby" in request.product.lower():
        mock_recalls.append({
            "recall_id": "R2024-001",
            "product_name": "Baby Product Example",
            "brand": "TestBrand",
            "hazard": "Choking hazard",
            "recall_date": "2024-01-15",
            "source_agency": "CPSC"
        })
    
    return SearchAdvancedResponse(
        total=len(mock_recalls),
        agencies=len(request.agencies) if request.agencies else 3,
        recalls=mock_recalls,
        cached=False
    )

@app.post("/api/v1/users")
async def create_user(email: str, password: str, is_subscribed: bool = False):
    """Create a new user"""
    logger.info(f"Creating user: {email}")
    
    return {
        "id": 1,
        "email": email,
        "is_subscribed": is_subscribed,
        "created_at": datetime.now().isoformat()
    }

@app.get("/api/v1/admin/system-stats")
async def system_stats():
    """Get system statistics"""
    return {
        "api_version": "1.0.0-test",
        "database": {
            "status": "ok",
            "total_recalls": 1000,
            "last_update": datetime.now().isoformat()
        },
        "cache": {"status": "disabled"},
        "performance": {
            "avg_response_time_ms": 50,
            "requests_today": 100
        }
    }

# Premium Features (Mocked)
@app.post("/api/v1/premium/pregnancy/check")
async def pregnancy_check(product: str, trimester: int):
    """Check product safety for pregnancy"""
    return {
        "product": product,
        "is_safe": True,
        "trimester": trimester,
        "warnings": [],
        "recommendations": ["Consult your healthcare provider"],
        "confidence": 0.85
    }

@app.post("/api/v1/premium/allergy/check")
async def allergy_check(product: str, allergies: List[str]):
    """Check product for allergens"""
    return {
        "product": product,
        "is_safe": True,
        "detected_allergens": [],
        "warnings": [],
        "alternatives": [],
        "confidence": 0.90
    }

# Baby Features (Mocked)
@app.post("/api/v1/baby/alternatives")
async def get_alternatives(product: str):
    """Get safe alternatives for a product"""
    return {
        "original_product": product,
        "alternatives": [
            {"name": f"Alternative 1 for {product}", "safety_score": 95},
            {"name": f"Alternative 2 for {product}", "safety_score": 92}
        ],
        "recommendations": ["Consider organic options"]
    }

# Advanced Features (Mocked)
@app.post("/api/v1/advanced/research")
async def web_research(query: str):
    """Perform web research on a product"""
    return {
        "query": query,
        "findings": ["Product is well-reviewed", "No recent safety concerns"],
        "sources": ["Consumer Reports", "FDA Database"],
        "timestamp": datetime.now().isoformat()
    }

# Compliance Features (Mocked)
@app.post("/api/v1/compliance/coppa/verify-age")
async def verify_age(birthdate: str):
    """Verify age for COPPA compliance"""
    return {
        "age": 15,
        "coppa_applies": False,
        "requires_parental_consent": False,
        "verification_status": "verified"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
