"""
Test Report Unsafe Product endpoint
"""

from datetime import datetime

import pytest


def test_report_unsafe_product_minimal_fields(client):
    """Test reporting unsafe product with minimal required fields"""

    payload = {
        "user_id": 12345,
        "product_name": "Dangerous Baby Crib",
        "hazard_description": "The mattress support collapsed causing the baby to fall through",
    }

    response = client.post("/api/v1/report-unsafe-product", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "report_id" in data
    assert data["status"] == "PENDING"
    assert "message" in data
    assert "created_at" in data


def test_report_unsafe_product_full_fields(client):
    """Test reporting unsafe product with all optional fields"""

    payload = {
        "user_id": 12345,
        "product_name": "Baby Dream Crib Model XL-2000",
        "hazard_description": "Mattress support collapsed causing baby to fall",
        "barcode": "0123456789012",
        "model_number": "XL-2000",
        "lot_number": "LOT-2025-001",
        "brand": "Baby Dream",
        "manufacturer": "Dream Products Inc.",
        "severity": "HIGH",
        "category": "Cribs",
        "reporter_name": "John Doe",
        "reporter_email": "john.doe@example.com",
        "reporter_phone": "+1-555-0100",
        "incident_date": "2025-10-01",
        "incident_description": "The crib mattress support suddenly collapsed...",
        "photos": ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
    }

    response = client.post("/api/v1/report-unsafe-product", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["report_id"] > 0
    assert data["status"] == "PENDING"


def test_report_unsafe_product_missing_required_fields(client):
    """Test that missing required fields returns 422"""

    payload = {
        "user_id": 12345,
        "product_name": "Test Product",
        # Missing hazard_description
    }

    response = client.post("/api/v1/report-unsafe-product", json=payload)
    assert response.status_code == 422


def test_report_unsafe_product_invalid_severity(client):
    """Test that invalid severity returns 422"""

    payload = {
        "user_id": 12345,
        "product_name": "Test Product",
        "hazard_description": "Test hazard description",
        "severity": "INVALID",
    }

    response = client.post("/api/v1/report-unsafe-product", json=payload)
    assert response.status_code == 422


def test_report_unsafe_product_too_many_photos(client):
    """Test that more than 10 photos returns 422"""

    payload = {
        "user_id": 12345,
        "product_name": "Test Product",
        "hazard_description": "Test hazard description",
        "photos": [f"https://example.com/photo{i}.jpg" for i in range(15)],
    }

    response = client.post("/api/v1/report-unsafe-product", json=payload)
    assert response.status_code == 422


def test_get_user_reports(client):
    """Test retrieving user reports"""

    # First, create a report
    payload = {
        "user_id": 12345,
        "product_name": "Test Product",
        "hazard_description": "Test hazard description",
    }

    create_response = client.post("/api/v1/report-unsafe-product", json=payload)
    assert create_response.status_code == 201

    # Now retrieve user reports
    response = client.get("/api/v1/user-reports/12345")

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "reports" in data
    assert len(data["reports"]) > 0


def test_get_user_reports_with_status_filter(client):
    """Test retrieving user reports with status filter"""

    response = client.get("/api/v1/user-reports/12345?status=PENDING")

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "reports" in data


def test_get_user_reports_with_pagination(client):
    """Test retrieving user reports with pagination"""

    response = client.get("/api/v1/user-reports/12345?limit=10&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert "limit" in data
    assert "offset" in data
    assert data["limit"] == 10
    assert data["offset"] == 0


def test_get_user_reports_empty(client):
    """Test retrieving reports for user with no reports"""

    response = client.get("/api/v1/user-reports/99999999")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["reports"] == []


@pytest.mark.skip(reason="Rate limiting test - run manually to avoid CI delays")
def test_report_unsafe_product_rate_limiting(client):
    """Test that rate limiting prevents spam (10 reports per hour)"""

    base_payload = {
        "user_id": 12345,
        "product_name": "Test Product",
        "hazard_description": "Test hazard description",
    }

    # Submit 10 reports (should all succeed)
    for i in range(10):
        payload = {**base_payload, "product_name": f"Test Product {i}"}
        response = client.post("/api/v1/report-unsafe-product", json=payload)
        assert response.status_code == 201

    # 11th report should be rate limited
    response = client.post("/api/v1/report-unsafe-product", json=base_payload)
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()
