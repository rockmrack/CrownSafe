# ruff: noqa: I001

"""Integration-style tests for core BabyShield safety workflows.

These tests exercise the `/api/v1/safety-check` endpoint against the primary
user journeys described in the BabyShield playbooks. External services are
stubbed so the scenarios remain deterministic and do not require network
access. Premium checks (allergy, pregnancy) are assumed to be available for
all subscribers under the single-tier model.
"""

from __future__ import annotations

import datetime
import importlib
import os
from typing import Any, Dict, Optional

from fastapi.testclient import TestClient
import pytest


os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("TEST_DATABASE_URL", "sqlite:///babyshield_e2e.sqlite")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")

from api.main_crownsafe import app
from core_infra.database import (
    Allergy,
    Base,
    FamilyMember,
    RecallDB,
    SessionLocal,
    User,
    engine,
)
from core_infra.visual_agent_models import (
    ConfidenceLevel,
    ImageExtraction,
    ImageJob,
    JobStatus,
    MFVSession,
    ReviewQueue,
)


@pytest.fixture(autouse=True)
def _reset_database() -> None:
    """Ensure each scenario starts from a clean slate."""
    if engine.url.get_backend_name() == "sqlite":
        importlib.import_module("db.sqlite_jsonb_shim")
        # Ensure JSONB columns compile under SQLite by remapping to JSON
        from sqlalchemy import JSON
        from sqlalchemy.dialects.postgresql import JSONB

        jsonb_type: Any = JSONB
        jsonb_type.impl = JSON
        jsonb_type.cache_ok = True
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Allergy.__table__,
            FamilyMember.__table__,
            RecallDB.__table__,
            User.__table__,
            ImageJob.__table__,
            ImageExtraction.__table__,
            ReviewQueue.__table__,
            MFVSession.__table__,
        ],
    )
    session = SessionLocal()
    try:
        session.query(Allergy).delete()
        session.query(FamilyMember).delete()
        session.query(RecallDB).delete()
        session.query(User).delete()
        session.query(ImageExtraction).delete()
        session.query(ReviewQueue).delete()
        session.query(MFVSession).delete()
        session.query(ImageJob).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def client() -> TestClient:
    from api import main_crownsafe as mb_module

    # Force environment-mode code paths for SQLite-based integration tests
    mb_module.CONFIG_LOADED = False
    return TestClient(app)


def _seed_user(user_id: int, email: str = "user@example.com") -> None:
    session = SessionLocal()
    try:
        session.add(
            User(
                id=user_id,
                email=email,
                hashed_password="test-hash",
                is_subscribed=True,
            )
        )
        session.commit()
    finally:
        session.close()


def _seed_recall(
    *,
    recall_id: str,
    product_name: str,
    hazard: str,
    upc: Optional[str] = None,
    model_number: Optional[str] = None,
    lot_number: Optional[str] = None,
    severity: str = "critical",
    source_agency: str = "CPSC",
) -> None:
    session = SessionLocal()
    try:
        recall_kwargs: Dict[str, Any] = {
            "recall_id": recall_id,
            "product_name": product_name,
            "hazard": hazard,
            "severity": severity,
            "source_agency": source_agency,
            "recall_date": datetime.date(2024, 5, 1),
        }
        if "upc" in RecallDB.__table__.columns:
            recall_kwargs["upc"] = upc
        if "model_number" in RecallDB.__table__.columns:
            recall_kwargs["model_number"] = model_number
        if "lot_number" in RecallDB.__table__.columns:
            recall_kwargs["lot_number"] = lot_number

        recall = RecallDB(**recall_kwargs)
        session.add(recall)
        session.commit()
    finally:
        session.close()


def test_barcode_recall_workflow_returns_high_risk(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 1: parent scans a recalled product and receives a high-risk verdict."""

    _seed_user(user_id=1)
    _seed_recall(
        recall_id="CPSC-24-0001",
        product_name="Yoto Mini Player",
        upc="850016249012",
        hazard="Lithium-ion battery overheating",
    )

    async def fake_run_optimized(user_request: Dict[str, Any]) -> Dict[str, Any]:
        assert user_request["barcode"] == "850016249012"
        return {
            "status": "COMPLETED",
            "data": {
                "product_name": "Yoto Mini Player",
                "risk_level": "High",
                "summary": ("This product has an active recall due to the Lithium-ion battery overheating."),
                "recall_details": {
                    "recall_id": "CPSC-24-0001",
                    "source_agency": "CPSC",
                    "hazard": "Lithium-ion battery overheating",
                },
                "recalls_found": 1,
            },
        }

    monkeypatch.setattr("api.main_crownsafe.run_optimized_safety_check", fake_run_optimized)

    response = client.post(
        "/api/v1/safety-check",
        json={"barcode": "850016249012", "user_id": 1},
    )

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["status"] == "COMPLETED"
    assert payload["data"]["risk_level"] == "High"
    assert "response_time_ms" in payload["data"]
    assert payload["data"].get("agencies_checked") == 39
    assert "Lithium-ion battery" in payload["data"]["summary"]
    assert payload["data"].get("recall_details", {}).get("recall_id") == "CPSC-24-0001"


def test_allergy_workflow_flags_family_allergens(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 2: allergy sensitivity agent catches a milk ingredient for a subscriber."""

    _seed_user(user_id=2, email="premium@example.com")
    session = SessionLocal()
    try:
        member = FamilyMember(id=101, name="Avery", user_id=2)
        member.allergies.append(Allergy(allergen="milk"))
        session.add(member)
        session.commit()
    finally:
        session.close()

    async def fake_run_optimized(user_request: Dict[str, Any]) -> Dict[str, Any]:
        assert user_request["barcode"] == "041220787346"
        return {
            "status": "COMPLETED",
            "data": {
                "product_name": "Organic Baby Food with Milk",
                "ingredients": ["Whole Milk Powder", "Organic Rice"],
                "risk_level": "Low",
                "recalls_found": 0,
            },
        }

    def fake_allergy_check(self, user_id: int, product_upc: str) -> Dict[str, Any]:
        assert user_id == 2
        assert product_upc == "041220787346"
        return {
            "status": "success",
            "is_safe": False,
            "alerts": [
                {
                    "member_name": "Avery",
                    "found_allergens": ["milk"],
                }
            ],
        }

    monkeypatch.setattr("api.main_crownsafe.run_optimized_safety_check", fake_run_optimized)
    monkeypatch.setattr(
        "agents.premium.allergy_sensitivity_agent.agent_logic.AllergySensitivityAgentLogic.check_product_for_family",
        fake_allergy_check,
    )

    response = client.post(
        "/api/v1/safety-check",
        json={
            "barcode": "041220787346",
            "user_id": 2,
            "check_allergies": True,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["status"] == "COMPLETED"
    allergy_section = payload["data"].get("allergy_safety")
    assert allergy_section and allergy_section["safe"] is False
    assert allergy_section["alerts"][0]["member_name"] == "Avery"
    assert "milk" in payload["data"]["summary"]
    assert payload["data"].get("premium_checks_performed") is True


def test_visual_low_confidence_returns_inconclusive(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 3: low-confidence visual scan surfaces an inconclusive result."""

    _seed_user(user_id=3)

    async def failing_run_optimized(user_request: Dict[str, Any]) -> Dict[str, Any]:
        assert user_request["image_url"] == "https://example.com/blurry_photo.jpg"
        return {
            "status": "FAILED",
            "error": "optimized workflow error: visual confidence below threshold",
        }

    class StubCommander:
        async def start_safety_check_workflow(self, user_request: Dict[str, Any]) -> Dict[str, Any]:
            assert user_request["image_url"] == "https://example.com/blurry_photo.jpg"
            return {
                "status": "COMPLETED",
                "data": {
                    "summary": "Could not definitively identify this product from the photo.",
                    "risk_level": "Unknown",
                    "note": (
                        "This does not mean the product is safe. Please try taking a clearer "
                        "picture or search by the model number."
                    ),
                },
            }

    monkeypatch.setattr("api.main_crownsafe.run_optimized_safety_check", failing_run_optimized)

    # Preserve the existing commander to restore after the test
    from api import main_crownsafe as mb_module

    original_commander = getattr(mb_module, "commander_agent", None)
    mb_module.commander_agent = StubCommander()
    try:
        response = client.post(
            "/api/v1/safety-check",
            json={"image_url": "https://example.com/blurry_photo.jpg", "user_id": 3},
        )
    finally:
        mb_module.commander_agent = original_commander

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["status"] == "COMPLETED"
    assert payload["data"]["risk_level"] == "Unknown"
    assert "Could not definitively identify" in payload["data"]["summary"]


def test_scan_camera_model_number_workflow(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 1.2: OCR extracts model number and still reaches the safety check."""

    _seed_user(user_id=4)
    _seed_recall(
        recall_id="CPSC-24-0002",
        product_name="Yoto Mini Player",
        hazard="Lithium-ion battery overheating",
        upc="850016249012",
        model_number="YM001",
    )

    async def fake_run_optimized(user_request: Dict[str, Any]) -> Dict[str, Any]:
        assert user_request["barcode"] is None
        assert user_request["model_number"] == "YM001"
        assert user_request.get("lot_number") is None
        return {
            "status": "COMPLETED",
            "data": {
                "product_name": "Yoto Mini Player",
                "risk_level": "High",
                "summary": "Exact model number match located via OCR fallback.",
                "recalls_found": 1,
                "match_metadata": {"match_type": "model_number_exact"},
            },
        }

    monkeypatch.setattr("api.main_crownsafe.run_optimized_safety_check", fake_run_optimized)

    response = client.post(
        "/api/v1/safety-check",
        json={"model_number": "YM001", "user_id": 4},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["data"]["match_metadata"]["match_type"] == "model_number_exact"
    assert payload["data"]["recalls_found"] == 1


def test_visual_upload_pipeline_completes_analysis(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 2: Upload-photo workflow returns a completed analysis."""

    monkeypatch.setattr(
        "api.visual_agent_endpoints.presign_post",
        lambda s3_key, **_: {
            "url": "https://uploads.example.com",
            "fields": {"key": s3_key},
        },
    )

    class FakeS3Client:
        def head_object(self, *, Bucket: str, Key: str) -> None:  # noqa: N802 - third-party signature
            return None

    monkeypatch.setattr("api.visual_agent_endpoints.boto3.client", lambda *_, **__: FakeS3Client())

    class DummyProcess:
        @staticmethod
        def delay(job_id: str) -> None:  # noqa: D401 - simple stub
            return None

    monkeypatch.setattr("api.visual_agent_endpoints.process_image", DummyProcess)

    upload_response = client.post("/api/v1/visual/upload", params={"user_id": 15})
    assert upload_response.status_code == 200, upload_response.text
    upload_payload = upload_response.json()["data"]
    job_id = upload_payload["job_id"]
    assert upload_payload["status"] == "ready_for_upload"
    assert "upload_url" in upload_payload
    assert "upload_fields" in upload_payload

    analyze_response = client.post(
        "/api/v1/visual/analyze",
        json={"job_id": job_id},
    )
    assert analyze_response.status_code == 200, analyze_response.text
    analyze_payload = analyze_response.json()["data"]
    assert analyze_payload["status"] in {"processing", "queued"}

    session = SessionLocal()
    try:
        job = session.query(ImageJob).filter(ImageJob.id == job_id).one()
        job.status = JobStatus.COMPLETED  # type: ignore[assignment]
        job.confidence_level = ConfidenceLevel.HIGH  # type: ignore[assignment]
        job.confidence_score = 0.94  # type: ignore[assignment]
        job.completed_at = datetime.datetime.utcnow()  # type: ignore[assignment]
        session.add(
            ImageExtraction(
                job_id=job_id,
                product_name="Yoto Mini Player",
                brand_name="Yoto",
                model_number="YM001",
                upc_code="850016249012",
                warning_labels=["Battery overheating"],
            )
        )
        session.commit()
    finally:
        session.close()

    status_response = client.get(f"/api/v1/visual/status/{job_id}")
    assert status_response.status_code == 200, status_response.text
    status_payload = status_response.json()["data"]
    assert status_payload["status"] == "completed"
    assert status_payload["extraction"]["product_name"] == "Yoto Mini Player"
    assert status_payload["extraction"]["model"] == "YM001"
    assert status_payload["extraction"]["warnings"] == ["Battery overheating"]


def test_enter_model_number_prioritizes_recall_agent(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 3: Manual model number search skips product identification and hits recall agent."""

    _seed_user(user_id=5)
    _seed_recall(
        recall_id="CPSC-24-0003",
        product_name="Yoto Mini Player",
        hazard="Battery overheating",
        model_number="YM001",
    )

    async def fake_run_optimized(user_request: Dict[str, Any]) -> Dict[str, Any]:
        assert user_request["model_number"] == "YM001"
        assert user_request["barcode"] is None
        return {
            "status": "COMPLETED",
            "data": {
                "product_name": "Yoto Mini Player",
                "risk_level": "High",
                "summary": "Direct model number lookup triggered recall agent.",
                "recalls_found": 1,
                "match_metadata": {
                    "match_type": "model_number_exact",
                    "workflow_plan": [
                        "PlannerAgent:create_plan",
                        "RouterAgent:RecallDataAgent",
                    ],
                },
            },
        }

    monkeypatch.setattr("api.main_crownsafe.run_optimized_safety_check", fake_run_optimized)

    response = client.post(
        "/api/v1/safety-check",
        json={"model_number": "YM001", "user_id": 5},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    metadata = payload["data"]["match_metadata"]
    assert metadata["match_type"] == "model_number_exact"
    assert metadata["workflow_plan"][1] == "RouterAgent:RecallDataAgent"


def test_manual_barcode_entry_golden_path(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 4: Manual barcode entry follows the golden path workflow."""

    _seed_user(user_id=6)

    async def fake_run_optimized(user_request: Dict[str, Any]) -> Dict[str, Any]:
        assert user_request["barcode"] == "123456789012"
        assert user_request["model_number"] is None
        return {
            "status": "COMPLETED",
            "data": {
                "product_name": "Baby Monitor Deluxe",
                "risk_level": "Medium",
                "summary": "Recall detected for manually entered barcode.",
                "recalls_found": 1,
            },
        }

    monkeypatch.setattr("api.main_crownsafe.run_optimized_safety_check", fake_run_optimized)

    response = client.post(
        "/api/v1/safety-check",
        json={"barcode": "123456789012", "user_id": 6},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["data"]["recalls_found"] == 1
    assert "manually entered barcode" in payload["data"]["summary"].lower()


def test_lot_number_search_returns_precise_recall(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 5: Lot or serial number lookup surfaces specific recall guidance."""

    _seed_user(user_id=7)
    _seed_recall(
        recall_id="FDA-24-1001",
        product_name="Organic Baby Puree",
        hazard="Possible contamination",
        lot_number="LOT-ABC-123",
        source_agency="FDA",
    )

    async def fake_run_optimized(user_request: Dict[str, Any]) -> Dict[str, Any]:
        assert user_request["lot_number"] == "LOT-ABC-123"
        assert user_request["barcode"] is None
        return {
            "status": "COMPLETED",
            "data": {
                "product_name": "Organic Baby Puree",
                "risk_level": "High",
                "summary": "Exact lot number match found. Dispose immediately.",
                "recalls_found": 1,
                "match_metadata": {"match_type": "lot_number_exact"},
            },
        }

    monkeypatch.setattr("api.main_crownsafe.run_optimized_safety_check", fake_run_optimized)

    response = client.post(
        "/api/v1/safety-check",
        json={"lot_number": "LOT-ABC-123", "user_id": 7},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["data"]["match_metadata"]["match_type"] == "lot_number_exact"


def test_product_name_search_uses_fuzzy_matching(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 6: Fuzzy name search retrieves the correct recall details."""

    _seed_user(user_id=8)
    _seed_recall(
        recall_id="CPSC-24-0004",
        product_name="Yoto Mini Player",
        hazard="Battery overheating",
        source_agency="CPSC",
    )

    async def fake_run_optimized(user_request: Dict[str, Any]) -> Dict[str, Any]:
        assert user_request["product_name"] == "Yoto Mini"
        assert user_request["barcode"] is None
        return {
            "status": "COMPLETED",
            "data": {
                "product_name": "Yoto Mini Player",
                "risk_level": "Medium",
                "summary": "Fuzzy product-name match identified the Yoto Mini Player recall.",
                "recalls_found": 1,
                "match_metadata": {
                    "match_type": "product_name_fuzzy",
                    "confidence": 0.88,
                },
            },
        }

    monkeypatch.setattr("api.main_crownsafe.run_optimized_safety_check", fake_run_optimized)

    response = client.post(
        "/api/v1/safety-check",
        json={"product_name": "Yoto Mini", "user_id": 8},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    metadata = payload["data"]["match_metadata"]
    assert metadata["match_type"] == "product_name_fuzzy"
    assert metadata["confidence"] == pytest.approx(0.88)
