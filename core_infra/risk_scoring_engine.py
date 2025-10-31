"""
Dynamic Risk Scoring Engine for Product Safety Assessment
Implements weighted scoring model based on CPSC penalty factors
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from core_infra.risk_assessment_models import (
    CompanyComplianceProfile,
    ProductGoldenRecord,
    SafetyIncident,
)

logger = logging.getLogger(__name__)


class RiskFactor(Enum):
    """Risk factors with their default weights"""

    SEVERITY_OF_HARM = 0.35  # 35% - Deaths, injuries, medical treatment
    RECENCY_OF_INCIDENT = 0.20  # 20% - How recent are the issues
    TOTAL_UNITS_AFFECTED = 0.15  # 15% - Scale of potential harm
    VIOLATION_TYPE = 0.15  # 15% - Nature of the defect
    COMPANY_COMPLIANCE = 0.15  # 15% - Company's track record


@dataclass
class RiskScoreComponents:
    """Detailed breakdown of risk score calculation"""

    severity_score: float = 0.0
    severity_details: Dict = None

    recency_score: float = 0.0
    recency_details: Dict = None

    volume_score: float = 0.0
    volume_details: Dict = None

    violation_score: float = 0.0
    violation_details: Dict = None

    compliance_score: float = 0.0
    compliance_details: Dict = None

    total_score: float = 0.0
    risk_level: str = "low"
    confidence: float = 0.0


class RiskScoringEngine:
    """
    Core risk scoring engine
    Calculates dynamic risk scores based on multiple weighted factors
    """

    def __init__(self, custom_weights: Optional[Dict[RiskFactor, float]] = None):
        """
        Initialize with optional custom weights
        Weights must sum to 1.0
        """
        self.weights = custom_weights or {factor: factor.value for factor in RiskFactor}

        # Validate weights (allow small floating point errors)
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.001:  # Allow 0.1% tolerance for floating point errors
            # Normalize weights to sum to 1.0
            self.weights = {k: v / total_weight for k, v in self.weights.items()}

        # Define severity classifications (aligned with FDA/CPSC)
        self.severity_classifications = {
            "death": 100,
            "serious_injury": 80,
            "moderate_injury": 60,
            "minor_injury": 40,
            "potential_harm": 20,
            "no_injury": 5,
        }

        # Hazard type severity mappings
        self.hazard_severity = {
            "choking": 90,
            "suffocation": 90,
            "strangulation": 90,
            "fire": 85,
            "burn": 80,
            "electric_shock": 80,
            "laceration": 70,
            "poisoning": 85,
            "chemical": 75,
            "fall": 65,
            "entrapment": 70,
            "drowning": 95,
            "lead": 85,
            "sharp_edge": 60,
            "tip_over": 70,
            "defective_latch": 50,
            "labeling": 20,
        }

    def calculate_risk_score(
        self,
        product: ProductGoldenRecord,
        incidents: List[SafetyIncident],
        company_profile: Optional[CompanyComplianceProfile],
        db: Session,
    ) -> RiskScoreComponents:
        """
        Calculate comprehensive risk score for a product

        Args:
            product: Product golden record
            incidents: List of safety incidents
            company_profile: Company compliance history
            db: Database session

        Returns:
            RiskScoreComponents with detailed breakdown
        """
        components = RiskScoreComponents()

        # 1. Calculate Severity Score (35%)
        (
            components.severity_score,
            components.severity_details,
        ) = self._calculate_severity_score(product, incidents)

        # 2. Calculate Recency Score (20%)
        (
            components.recency_score,
            components.recency_details,
        ) = self._calculate_recency_score(product, incidents, db)

        # 3. Calculate Volume Score (15%)
        (
            components.volume_score,
            components.volume_details,
        ) = self._calculate_volume_score(product, db)

        # 4. Calculate Violation Score (15%)
        (
            components.violation_score,
            components.violation_details,
        ) = self._calculate_violation_score(product, incidents, db)

        # 5. Calculate Compliance Score (15%)
        if company_profile:
            (
                components.compliance_score,
                components.compliance_details,
            ) = self._calculate_compliance_score(company_profile)

        # Calculate weighted total score
        components.total_score = (
            components.severity_score * self.weights[RiskFactor.SEVERITY_OF_HARM]
            + components.recency_score * self.weights[RiskFactor.RECENCY_OF_INCIDENT]
            + components.volume_score * self.weights[RiskFactor.TOTAL_UNITS_AFFECTED]
            + components.violation_score * self.weights[RiskFactor.VIOLATION_TYPE]
            + components.compliance_score * self.weights[RiskFactor.COMPANY_COMPLIANCE]
        )

        # Determine risk level
        components.risk_level = self._determine_risk_level(components.total_score)

        # Calculate confidence based on data completeness
        components.confidence = self._calculate_confidence(product, incidents, company_profile)

        return components

    def _calculate_severity_score(
        self, product: ProductGoldenRecord, incidents: List[SafetyIncident]
    ) -> Tuple[float, Dict]:
        """
        Calculate severity score based on injuries, deaths, and hazard types
        Returns score 0-100 and details dictionary
        """
        score = 0.0
        details = {
            "total_deaths": 0,
            "total_injuries": 0,
            "injury_types": {},
            "hazard_types": [],
            "severity_classification": "no_injury",
        }

        # Aggregate incident data
        for incident in incidents:
            if incident.incident_type == "death":
                details["total_deaths"] += 1
                details["severity_classification"] = "death"
            elif incident.incident_type == "injury":
                details["total_injuries"] += 1

                # Track injury types
                injury_type = incident.severity or "unknown"
                details["injury_types"][injury_type] = details["injury_types"].get(injury_type, 0) + 1

            # Track hazard types
            if incident.hazard_type and incident.hazard_type not in details["hazard_types"]:
                details["hazard_types"].append(incident.hazard_type)

        # Calculate base score from incidents
        if details["total_deaths"] > 0:
            score = 100  # Maximum severity for any death
        elif details["total_injuries"] > 0:
            # Scale based on number and type of injuries
            injury_score = min(80, 40 + (details["total_injuries"] * 5))

            # Adjust for injury severity
            if "serious" in details["injury_types"] or "hospitalized" in details["injury_types"]:
                injury_score = min(90, injury_score + 20)

            score = injury_score
        else:
            # No incidents but check hazard potential
            score = 20  # Base score for recalled product

        # Adjust for hazard types
        if details["hazard_types"]:
            max_hazard_score = max(self.hazard_severity.get(hazard.lower(), 50) for hazard in details["hazard_types"])
            score = max(score, max_hazard_score)

        details["final_score"] = score
        return score, details

    def _calculate_recency_score(
        self, product: ProductGoldenRecord, incidents: List[SafetyIncident], db: Session
    ) -> Tuple[float, Dict]:
        """
        Calculate recency score based on how recent incidents/recalls are
        More recent = higher risk
        """
        score = 0.0
        details = {
            "most_recent_incident": None,
            "incidents_last_year": 0,
            "incidents_last_6_months": 0,
            "incidents_last_3_months": 0,
            "time_since_last_incident": None,
        }

        now = datetime.utcnow()

        # Find most recent incident
        if incidents:
            recent_incident = max(incidents, key=lambda i: i.incident_date or datetime.min)
            if recent_incident.incident_date:
                details["most_recent_incident"] = recent_incident.incident_date
                days_since = (now - recent_incident.incident_date).days
                details["time_since_last_incident"] = days_since

                # Count incidents by recency
                for incident in incidents:
                    if incident.incident_date:
                        days_ago = (now - incident.incident_date).days
                        if days_ago <= 365:
                            details["incidents_last_year"] += 1
                        if days_ago <= 180:
                            details["incidents_last_6_months"] += 1
                        if days_ago <= 90:
                            details["incidents_last_3_months"] += 1

                # Calculate score based on recency
                if days_since <= 30:
                    score = 100  # Very recent
                elif days_since <= 90:
                    score = 80
                elif days_since <= 180:
                    score = 60
                elif days_since <= 365:
                    score = 40
                elif days_since <= 730:  # 2 years
                    score = 20
                else:
                    score = 10

                # Adjust for frequency
                if details["incidents_last_3_months"] > 3:
                    score = min(100, score + 20)
                elif details["incidents_last_6_months"] > 5:
                    score = min(100, score + 10)

        details["final_score"] = score
        return score, details

    def _calculate_volume_score(self, product: ProductGoldenRecord, db: Session) -> Tuple[float, Dict]:
        """
        Calculate volume score based on units affected
        More units = higher risk
        """
        score = 0.0
        details = {
            "total_units_recalled": 0,
            "estimated_units_in_market": 0,
            "distribution_scope": "unknown",
        }

        # Get total units from all recalls
        # This would query recall data linked to the product
        # For now, using placeholder logic

        units_recalled = 0  # Would come from recall data

        if product.risk_profile:
            units_recalled = product.risk_profile.units_affected or 0

        details["total_units_recalled"] = units_recalled

        # Calculate score based on volume
        if units_recalled >= 1000000:
            score = 100  # Million+ units
            details["distribution_scope"] = "massive"
        elif units_recalled >= 100000:
            score = 80
            details["distribution_scope"] = "very_large"
        elif units_recalled >= 10000:
            score = 60
            details["distribution_scope"] = "large"
        elif units_recalled >= 1000:
            score = 40
            details["distribution_scope"] = "moderate"
        elif units_recalled >= 100:
            score = 20
            details["distribution_scope"] = "small"
        elif units_recalled > 0:
            score = 10
            details["distribution_scope"] = "minimal"

        details["final_score"] = score
        return score, details

    def _calculate_violation_score(
        self, product: ProductGoldenRecord, incidents: List[SafetyIncident], db: Session
    ) -> Tuple[float, Dict]:
        """
        Calculate violation score based on type and severity of violations
        """
        score = 0.0
        details = {
            "violation_types": [],
            "repeat_violations": False,
            "mandatory_standard_violations": [],
            "voluntary_standard_violations": [],
        }

        # Collect violation types from incidents
        violation_types = set()
        for incident in incidents:
            if incident.hazard_type:
                violation_types.add(incident.hazard_type)

        details["violation_types"] = list(violation_types)

        # Check for high-severity violations
        high_severity_violations = [
            "choking",
            "suffocation",
            "strangulation",
            "fire",
            "lead",
            "chemical",
            "poisoning",
        ]

        found_high_severity = [v for v in violation_types if any(hsv in v.lower() for hsv in high_severity_violations)]

        if found_high_severity:
            score = 80
            details["mandatory_standard_violations"] = found_high_severity
        elif violation_types:
            score = 50

        # Check for repeat violations (would need historical data)
        # For now, if multiple incidents of same type
        violation_counts = {}
        for incident in incidents:
            if incident.hazard_type:
                violation_counts[incident.hazard_type] = violation_counts.get(incident.hazard_type, 0) + 1

        if any(count > 2 for count in violation_counts.values()):
            details["repeat_violations"] = True
            score = min(100, score + 20)

        details["final_score"] = score
        return score, details

    def _calculate_compliance_score(self, company_profile: CompanyComplianceProfile) -> Tuple[float, Dict]:
        """
        Calculate compliance score based on company history
        Poor compliance = higher risk
        """
        score = 0.0
        details = {
            "total_recalls": company_profile.total_recalls,
            "recent_recalls": company_profile.recent_recalls,
            "total_penalties": company_profile.total_penalties,
            "repeat_offender": company_profile.repeat_offender,
            "compliance_trend": company_profile.compliance_trend,
        }

        # Base score on compliance history
        if company_profile.repeat_offender:
            score = 80
        elif company_profile.recent_recalls > 3:
            score = 70
        elif company_profile.recent_recalls > 1:
            score = 50
        elif company_profile.total_recalls > 5:
            score = 40
        elif company_profile.total_recalls > 0:
            score = 20
        else:
            score = 0  # Clean record

        # Adjust for compliance trend
        if company_profile.compliance_trend == "declining":
            score = min(100, score + 20)
        elif company_profile.compliance_trend == "improving":
            score = max(0, score - 10)

        # Adjust for penalties
        if company_profile.total_penalty_amount > 1000000:
            score = min(100, score + 20)
        elif company_profile.total_penalty_amount > 100000:
            score = min(100, score + 10)

        details["final_score"] = score
        return score, details

    def _determine_risk_level(self, total_score: float) -> str:
        """
        Determine risk level based on total score
        """
        if total_score >= 75:
            return "critical"
        elif total_score >= 50:
            return "high"
        elif total_score >= 25:
            return "medium"
        else:
            return "low"

    def _calculate_confidence(
        self,
        product: ProductGoldenRecord,
        incidents: List[SafetyIncident],
        company_profile: Optional[CompanyComplianceProfile],
    ) -> float:
        """
        Calculate confidence in the risk score based on data completeness
        """
        confidence = 0.0

        # Product data completeness
        product_fields = [
            product.gtin,
            product.upc,
            product.brand,
            product.manufacturer,
            product.model_number,
        ]
        product_completeness = sum(1 for f in product_fields if f) / len(product_fields)
        confidence += product_completeness * 0.3

        # Incident data quality
        if incidents:
            confidence += 0.3
            if len(incidents) > 5:
                confidence += 0.1

        # Company data availability
        if company_profile:
            confidence += 0.2

        # Data source diversity
        if product.data_sources:
            source_types = set(ds.source_type for ds in product.data_sources)
            if len(source_types) > 3:
                confidence += 0.1

        return min(confidence, 1.0)

    def calculate_trend(self, historical_scores: List[Tuple[datetime, float]]) -> str:
        """
        Calculate risk trend from historical scores
        Returns: "increasing", "stable", or "decreasing"
        """
        if len(historical_scores) < 2:
            return "stable"

        # Sort by date
        sorted_scores = sorted(historical_scores, key=lambda x: x[0])

        # Calculate trend over last 3 data points
        recent_scores = sorted_scores[-3:]

        if len(recent_scores) < 2:
            return "stable"

        # Simple linear trend
        first_score = recent_scores[0][1]
        last_score = recent_scores[-1][1]

        change = last_score - first_score

        if change > 10:
            return "increasing"
        elif change < -10:
            return "decreasing"
        else:
            return "stable"

    def generate_risk_narrative(self, components: RiskScoreComponents) -> str:
        """
        Generate human-readable risk narrative
        """
        narrative = []

        # Overall assessment
        narrative.append(f"Risk Level: {components.risk_level.upper()}")
        narrative.append(f"Risk Score: {components.total_score:.1f}/100")
        narrative.append(f"Confidence: {components.confidence:.0%}\n")

        # Key risk factors
        narrative.append("Key Risk Factors:")

        if components.severity_details and components.severity_details.get("total_deaths") > 0:
            narrative.append(f"• CRITICAL: {components.severity_details['total_deaths']} death(s) reported")

        if components.severity_details and components.severity_details.get("total_injuries") > 0:
            narrative.append(f"• {components.severity_details['total_injuries']} injuries reported")

        if components.recency_details and components.recency_details.get("incidents_last_3_months") > 0:
            narrative.append(f"• {components.recency_details['incidents_last_3_months']} incidents in last 3 months")

        if components.volume_details and components.volume_details.get("total_units_recalled") > 10000:
            narrative.append(f"• {components.volume_details['total_units_recalled']:,} units affected")

        if components.violation_details and components.violation_details.get("repeat_violations"):
            narrative.append("• Repeat violations detected")

        if components.compliance_details and components.compliance_details.get("repeat_offender"):
            narrative.append("• Manufacturer is a repeat offender")

        return "\n".join(narrative)
