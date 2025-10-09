"""
Manufacturer verifier interface and a mock implementation.

The verifier takes unit-level identifiers (gtin, lot, serial, expiry) and
returns a structured verification result. Real OEM connectors can implement
the same interface and be configured via ENV.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Dict, Any


@dataclass
class VerificationInput:
    gtin: Optional[str]
    lot_number: Optional[str]
    serial_number: Optional[str]
    expiry_date: Optional[date]
    trace_id: Optional[str] = None


@dataclass
class VerificationResult:
    verified: bool
    status: str  # verified | invalid | unknown | error
    manufacturer: Optional[str] = None
    source: Optional[str] = None
    message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    checked_at: datetime = datetime.utcnow()


class ManufacturerVerifier:
    def verify(self, vin: VerificationInput) -> VerificationResult:
        raise NotImplementedError


class MockManufacturerVerifier(ManufacturerVerifier):
    """
    Simple rules for demo/testing:
    - If serial present and endswith an even digit: verified
    - If serial present and endswith an odd digit: invalid
    - If no serial but lot present: unknown (needs OEM)
    - Else: unknown
    """

    def __init__(self, manufacturer_name: str = "MockOEM"):
        self.manufacturer_name = manufacturer_name

    def verify(self, vin: VerificationInput) -> VerificationResult:
        serial = (vin.serial_number or "").strip()
        lot = (vin.lot_number or "").strip()

        if serial:
            last = serial[-1]
            if last.isdigit():
                if int(last) % 2 == 0:
                    return VerificationResult(
                        verified=True,
                        status="verified",
                        manufacturer=self.manufacturer_name,
                        source="mock",
                        message="Serial validated by mock rule",
                        payload={"rule": "even-last-digit"},
                    )
                else:
                    return VerificationResult(
                        verified=False,
                        status="invalid",
                        manufacturer=self.manufacturer_name,
                        source="mock",
                        message="Serial failed mock rule",
                        payload={"rule": "odd-last-digit"},
                    )
            # Non-digit ending → unknown
            return VerificationResult(
                verified=False,
                status="unknown",
                manufacturer=self.manufacturer_name,
                source="mock",
                message="Serial format not recognized by mock",
                payload={"reason": "nondigit"},
            )

        if lot:
            return VerificationResult(
                verified=False,
                status="unknown",
                manufacturer=self.manufacturer_name,
                source="mock",
                message="Lot present; OEM verification required",
                payload={"hint": "implement_oem_connector"},
            )

        return VerificationResult(
            verified=False,
            status="unknown",
            manufacturer=self.manufacturer_name,
            source="mock",
            message="Insufficient identifiers",
        )


def get_default_verifier() -> ManufacturerVerifier:
    # In future, route by env/config to OEM-specific connectors
    if os.getenv("USE_MOCK_VERIFIER", "true").lower() in ("true", "1", "yes"):
        return MockManufacturerVerifier()
    # Placeholder: return mock if no real connectors configured
    return MockManufacturerVerifier()
