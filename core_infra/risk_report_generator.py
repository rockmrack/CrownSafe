"""Risk Assessment Report Generator
Produces comprehensive product safety reports with legal disclaimers
"""

import json
import logging
import os
from datetime import datetime, timezone, UTC
from io import BytesIO
from typing import Any

from jinja2 import Environment, select_autoescape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core_infra.azure_storage import AzureBlobStorageClient
from core_infra.risk_assessment_models import (
    CompanyComplianceProfile,
    ProductGoldenRecord,
    ProductRiskProfile,
    SafetyIncident,
)
from core_infra.risk_scoring_engine import RiskScoreComponents

logger = logging.getLogger(__name__)


class RiskReportGenerator:
    jinja_html_env = Environment(
        autoescape=select_autoescape(
            enabled_extensions=("html", "xml"),
            default_for_string=True,
            default=True,
        ),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    RISK_REPORT_HTML_TEMPLATE = jinja_html_env.from_string(
        """
<!DOCTYPE html>
<html>
<head>
    <title>Product Safety Risk Assessment - {{ report_id }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background: #1a237e; color: white; padding: 20px; text-align: center; }
        .disclaimer { background: #ffebee; border: 2px solid red; padding: 15px; margin: 20px 0; }
        .risk-score { font-size: 48px; font-weight: bold; }
        .risk-{{ risk_level }} { color: {{ risk_color }}; }
        .section { margin: 30px 0; }
        .factor { background: #f5f5f5; padding: 15px; margin: 10px 0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border: 1px solid #ddd; }
        th { background: #e0e0e0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>PRODUCT SAFETY RISK ASSESSMENT</h1>
        <p>Report ID: {{ report_id }} | Generated: {{ generated_at }}</p>
    </div>
    
    <div class="disclaimer">
        <h2>⚠️ CRITICAL DISCLAIMERS</h2>
        <p><strong>{{ disclaimers.general }}</strong></p>
        <p>{{ disclaimers.ai_limitations }}</p>
    </div>
    
    <div class="section">
        <h2>Risk Summary</h2>
        <div class="risk-score risk-{{ risk_summary.level|lower }}">
            {{ risk_summary.score }}/100
        </div>
        <p>Risk Level: <strong>{{ risk_summary.level }}</strong></p>
        <p>Confidence: {{ risk_summary.confidence }}</p>
        <p>Trend: {{ risk_summary.trend }}</p>
    </div>
    
    <div class="section">
        <h2>Product Information</h2>
        <table>
            <tr><th>Product Name</th><td>{{ product.name }}</td></tr>
            <tr><th>Brand</th><td>{{ product.brand or 'Unknown' }}</td></tr>
            <tr><th>Manufacturer</th><td>{{ product.manufacturer or 'Unknown' }}</td></tr>
            <tr><th>Model</th><td>{{ product.model or 'N/A' }}</td></tr>
            <tr><th>GTIN/UPC</th><td>{{ product.gtin or product.upc or 'N/A' }}</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Risk Factor Analysis</h2>
        {% for factor_name, factor_data in risk_factors.items() %}
        <div class="factor">
            <h3>{{ factor_name|upper }} (Weight: {{ factor_data.weight }})</h3>
            <p>Score: {{ factor_data.score }}/100</p>
            {% if factor_data.details %}
            <ul>
                {% for key, value in factor_data.details.items() %}
                <li>{{ key }}: {{ value }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    {% if incidents %}
    <div class="section">
        <h2>Incident Summary</h2>
        <p>{{ incidents }}</p>
    </div>
    {% endif %}
    
    <div class="section">
        <h2>Recommendations</h2>
        <ol>
            {% for rec in recommendations %}
            <li>{{ rec }}</li>
            {% endfor %}
        </ol>
    </div>
    
    <div class="disclaimer">
        <h2>Legal Disclaimers</h2>
        {% for key, disclaimer in disclaimers.items() %}
        <p>{{ disclaimer }}</p>
        {% endfor %}
    </div>
</body>
</html>
""",
    )

    """
    Generates comprehensive risk assessment reports
    Supports multiple formats: PDF, HTML, JSON
    """

    def __init__(self, storage_client: AzureBlobStorageClient | None = None) -> None:
        self.storage_client = storage_client or AzureBlobStorageClient()
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER", "crownsafe-reports")

        # Legal disclaimers (CRITICAL - Never skip these)
        self.disclaimers = {
            "general": (
                "IMPORTANT DISCLAIMER: This report is generated by an AI-powered risk assessment system "
                "and is provided for INFORMATIONAL PURPOSES ONLY. The analysis may contain errors, "
                "omissions, or inaccuracies. This report is NOT a substitute for professional safety advice, "
                "legal counsel, or regulatory guidance."
            ),
            "ai_limitations": (
                "AI LIMITATIONS: The artificial intelligence models used in this analysis have inherent "
                "limitations and may produce incorrect classifications, miss critical safety issues, or "
                "generate false positives. Human verification is ALWAYS required before taking any action "
                "based on this report."
            ),
            "data_currency": (
                "DATA CURRENCY: This report is based on data available at the time of generation. "
                "Product safety information changes frequently. Always verify current recall status "
                "and safety information through official channels such as CPSC.gov or SaferProducts.gov."
            ),
            "no_warranty": (
                "NO WARRANTY: This report is provided 'AS IS' without any warranty of accuracy, "
                "completeness, or fitness for a particular purpose. The provider expressly disclaims "
                "all warranties, express or implied."
            ),
            "liability": (
                "LIMITATION OF LIABILITY: Under no circumstances shall the provider be liable for any "
                "direct, indirect, incidental, special, or consequential damages arising from the use "
                "of this report, even if advised of the possibility of such damages."
            ),
            "regulatory": (
                "REGULATORY COMPLIANCE: This report does not constitute official regulatory documentation. "
                "Users must ensure compliance with all applicable laws, regulations, and standards "
                "independently of this analysis."
            ),
            "action": (
                "RECOMMENDED ACTION: If you possess a product identified in this report, DO NOT rely "
                "solely on this analysis. Verify the information through official sources, check the "
                "product's official recall status, and follow manufacturer or regulatory agency guidance."
            ),
        }

    def generate_report(
        self,
        product: ProductGoldenRecord,
        risk_profile: ProductRiskProfile,
        risk_components: RiskScoreComponents,
        incidents: list[SafetyIncident],
        company_profile: CompanyComplianceProfile | None,
        format: str = "pdf",
    ) -> dict[str, Any]:
        """Generate comprehensive risk assessment report

        Args:
            product: Product golden record
            risk_profile: Product risk profile
            risk_components: Detailed risk score breakdown
            incidents: List of safety incidents
            company_profile: Company compliance history
            format: Output format (pdf, html, json)

        Returns:
            Dictionary with report URL and metadata

        """
        logger.info(f"Generating {format} report for product {product.id}")

        # Prepare report data
        report_data = self._prepare_report_data(product, risk_profile, risk_components, incidents, company_profile)

        # Generate report based on format
        if format == "pdf":
            report_content = self._generate_pdf_report(report_data)
        elif format == "html":
            report_content = self._generate_html_report(report_data)
        elif format == "json":
            report_content = self._generate_json_report(report_data)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Upload to Azure Blob Storage
        report_url = self._upload_to_azure_blob(report_content, product.id, format)

        # Create report record
        report_record = {
            "product_id": product.id,
            "report_type": "full",
            "generated_at": datetime.now(UTC),
            "report_version": "1.0",
            "risk_score": risk_components.total_score,
            "risk_level": risk_components.risk_level,
            "report_url": report_url,
            "report_format": format,
            "status": "published",
        }

        return report_record

    def _prepare_report_data(
        self,
        product: ProductGoldenRecord,
        risk_profile: ProductRiskProfile,
        risk_components: RiskScoreComponents,
        incidents: list[SafetyIncident],
        company_profile: CompanyComplianceProfile | None,
    ) -> dict:
        """Prepare all data for report generation"""
        data = {
            "report_id": f"RSK-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
            "generated_at": datetime.now(UTC).isoformat(),
            "product": {
                "name": product.product_name,
                "brand": product.brand,
                "manufacturer": product.manufacturer,
                "model": product.model_number,
                "gtin": product.gtin,
                "upc": product.upc,
                "category": product.product_category,
                "image": product.primary_image_url,
            },
            "risk_summary": {
                "score": round(risk_components.total_score, 1),
                "level": (risk_components.risk_level or "UNKNOWN").upper(),
                "confidence": f"{risk_components.confidence:.0%}",
                "trend": risk_profile.risk_trend if risk_profile else "stable",
            },
            "risk_factors": {
                "severity": {
                    "score": round(risk_components.severity_score, 1),
                    "weight": "35%",
                    "details": risk_components.severity_details,
                },
                "recency": {
                    "score": round(risk_components.recency_score, 1),
                    "weight": "20%",
                    "details": risk_components.recency_details,
                },
                "volume": {
                    "score": round(risk_components.volume_score, 1),
                    "weight": "15%",
                    "details": risk_components.volume_details,
                },
                "violations": {
                    "score": round(risk_components.violation_score, 1),
                    "weight": "15%",
                    "details": risk_components.violation_details,
                },
                "compliance": {
                    "score": round(risk_components.compliance_score, 1),
                    "weight": "15%",
                    "details": risk_components.compliance_details,
                },
            },
            "incidents": self._summarize_incidents(incidents),
            "company": self._summarize_company(company_profile) if company_profile else None,
            "recommendations": self._generate_recommendations(risk_components),
            "data_sources": self._list_data_sources(product),
            "disclaimers": self.disclaimers,
        }

        return data

    def _generate_pdf_report(self, data: dict) -> BytesIO:
        """Generate PDF report using ReportLab"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=24,
            textColor=colors.HexColor("#1a237e"),
            alignment=TA_CENTER,
        )

        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#283593"),
            spaceAfter=12,
        )

        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.red,
            borderColor=colors.red,
            borderWidth=1,
            borderPadding=5,
            backColor=colors.HexColor("#ffebee"),
        )

        # Title Page
        story.append(Paragraph("PRODUCT SAFETY RISK ASSESSMENT", title_style))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Report ID: {data['report_id']}", styles["Normal"]))
        story.append(Paragraph(f"Generated: {data['generated_at']}", styles["Normal"]))
        story.append(Spacer(1, 0.5 * inch))

        # CRITICAL DISCLAIMER - TOP OF REPORT
        story.append(Paragraph("⚠️ IMPORTANT DISCLAIMERS", heading_style))
        story.append(Paragraph(data["disclaimers"]["general"], disclaimer_style))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(data["disclaimers"]["ai_limitations"], disclaimer_style))
        story.append(PageBreak())

        # Executive Summary
        story.append(Paragraph("EXECUTIVE SUMMARY", heading_style))

        # Risk Score Visual
        risk_color = self._get_risk_color(data["risk_summary"]["level"])
        risk_table_data = [
            ["Risk Score", "Risk Level", "Confidence", "Trend"],
            [
                f"{data['risk_summary']['score']}/100",
                data["risk_summary"]["level"],
                data["risk_summary"]["confidence"],
                (data["risk_summary"]["trend"] or "UNKNOWN").upper(),
            ],
        ]
        risk_table = Table(risk_table_data, colWidths=[2 * inch, 2 * inch, 2 * inch, 2 * inch])
        risk_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), risk_color),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ],
            ),
        )
        story.append(risk_table)
        story.append(Spacer(1, 0.3 * inch))

        # Product Information
        story.append(Paragraph("PRODUCT INFORMATION", heading_style))
        product_data = [
            ["Product Name:", data["product"]["name"]],
            ["Brand:", data["product"]["brand"] or "Unknown"],
            ["Manufacturer:", data["product"]["manufacturer"] or "Unknown"],
            ["Model Number:", data["product"]["model"] or "N/A"],
            [
                "GTIN/UPC:",
                f"{data['product']['gtin'] or data['product']['upc'] or 'N/A'}",
            ],
            ["Category:", data["product"]["category"] or "Unknown"],
        ]
        product_table = Table(product_data, colWidths=[2 * inch, 5 * inch])
        product_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ],
            ),
        )
        story.append(product_table)
        story.append(Spacer(1, 0.3 * inch))

        # Risk Factor Analysis
        story.append(Paragraph("RISK FACTOR ANALYSIS", heading_style))

        for factor_name, factor_data in data["risk_factors"].items():
            factor_title = f"{factor_name.upper()} (Weight: {factor_data['weight']})"
            story.append(Paragraph(factor_title, styles["Heading2"]))
            story.append(Paragraph(f"Score: {factor_data['score']}/100", styles["Normal"]))

            if factor_data["details"]:
                details_text = self._format_details(factor_data["details"])
                story.append(Paragraph(details_text, styles["Normal"]))

            story.append(Spacer(1, 0.2 * inch))

        # Incident Summary
        if data["incidents"]:
            story.append(PageBreak())
            story.append(Paragraph("INCIDENT SUMMARY", heading_style))
            story.append(Paragraph(data["incidents"], styles["Normal"]))
            story.append(Spacer(1, 0.3 * inch))

        # Recommendations
        story.append(Paragraph("RECOMMENDATIONS", heading_style))
        for i, rec in enumerate(data["recommendations"], 1):
            story.append(Paragraph(f"{i}. {rec}", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # Data Sources
        story.append(Paragraph("DATA SOURCES", heading_style))
        story.append(Paragraph(data["data_sources"], styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # Final Disclaimers
        story.append(PageBreak())
        story.append(Paragraph("LEGAL DISCLAIMERS", heading_style))
        for key, disclaimer in data["disclaimers"].items():
            story.append(Paragraph(disclaimer, disclaimer_style))
            story.append(Spacer(1, 0.1 * inch))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    def _generate_html_report(self, data: dict) -> str:
        """Render HTML report with autoescaped template."""
        context = dict(data)
        context["risk_color"] = self._get_risk_color_hex(context["risk_summary"]["level"])
        context["risk_level"] = context["risk_summary"]["level"].lower()
        return self.RISK_REPORT_HTML_TEMPLATE.render(**context)

    def _generate_json_report(self, data: dict) -> str:
        """Generate JSON report"""

        # Ensure all data is JSON serializable
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)

        return json.dumps(data, default=serialize, indent=2)

    def _summarize_incidents(self, incidents: list[SafetyIncident]) -> str:
        """Create incident summary text"""
        if not incidents:
            return "No incidents reported."

        total = len(incidents)
        deaths = sum(1 for i in incidents if i.incident_type == "death")
        injuries = sum(1 for i in incidents if i.incident_type == "injury")

        summary = f"Total Incidents: {total}\n"
        if deaths > 0:
            summary += f"⚠️ DEATHS REPORTED: {deaths}\n"
        if injuries > 0:
            summary += f"Injuries Reported: {injuries}\n"

        # Recent incidents
        recent = [i for i in incidents if i.incident_date and (datetime.now(UTC) - i.incident_date).days < 90]
        if recent:
            summary += f"Recent Incidents (last 90 days): {len(recent)}\n"

        # Common hazards
        hazards = {}
        for incident in incidents:
            if incident.hazard_type:
                hazards[incident.hazard_type] = hazards.get(incident.hazard_type, 0) + 1

        if hazards:
            top_hazards = sorted(hazards.items(), key=lambda x: x[1], reverse=True)[:3]
            summary += "Top Hazards: " + ", ".join([f"{h[0]} ({h[1]})" for h in top_hazards])

        return summary

    def _summarize_company(self, company: CompanyComplianceProfile) -> str:
        """Create company summary text"""
        summary = f"Company: {company.company_name}\n"
        summary += f"Total Recalls: {company.total_recalls}\n"
        summary += f"Recent Recalls (12 months): {company.recent_recalls}\n"

        if company.repeat_offender:
            summary += "⚠️ REPEAT OFFENDER\n"

        if company.total_penalties > 0:
            summary += f"Total Penalties: {company.total_penalties} (${company.total_penalty_amount:,.2f})\n"

        summary += f"Compliance Trend: {company.compliance_trend}"

        return summary

    def _generate_recommendations(self, risk_components: RiskScoreComponents) -> list[str]:
        """Generate actionable recommendations based on risk analysis"""
        recommendations = []

        # Always include verification recommendation
        recommendations.append(
            "VERIFY all information in this report through official sources "
            "(CPSC.gov, manufacturer website, or retailer)",
        )

        # Risk level based recommendations
        if risk_components.risk_level == "critical":
            recommendations.append(
                "IMMEDIATE ACTION REQUIRED: Stop using this product immediately and check for active recalls",
            )
            recommendations.append("Contact the manufacturer or retailer for remedy information")
        elif risk_components.risk_level == "high":
            recommendations.append("Review product carefully for any defects or damage before use")
            recommendations.append("Monitor CPSC.gov for updates on this product")

        # Factor-specific recommendations
        if risk_components.severity_details and risk_components.severity_details.get("total_deaths") > 0:
            recommendations.append(
                "⚠️ CRITICAL: Deaths have been reported with this product. "
                "Exercise extreme caution and consider alternatives",
            )

        if risk_components.recency_details and risk_components.recency_details.get("incidents_last_3_months") > 0:
            recommendations.append("Recent incidents detected - check for the latest safety notices")

        if risk_components.violation_details and risk_components.violation_details.get("repeat_violations"):
            recommendations.append("Pattern of violations detected - consider alternative products")

        # General safety recommendations
        recommendations.append("Keep all product packaging and receipts for potential recalls")
        recommendations.append("Register your product with the manufacturer for direct recall notifications")
        recommendations.append("Report any safety issues to CPSC at SaferProducts.gov")

        return recommendations

    def _list_data_sources(self, product: ProductGoldenRecord) -> str:
        """List all data sources used"""
        sources = []

        if product.data_sources:
            for ds in product.data_sources:
                sources.append(f"• {ds.source_type}: {ds.source_name} (Updated: {ds.fetched_at})")

        if not sources:
            sources.append("• Internal database")

        sources.append("• CPSC Public Data API")
        sources.append("• EU Safety Gate Rapid Alert System")
        sources.append("• Commercial Product Databases")

        return "\n".join(sources)

    def _format_details(self, details: dict) -> str:
        """Format details dictionary as readable text"""
        if not details:
            return "No additional details available."

        lines = []
        for key, value in details.items():
            if value is not None and value != 0 and value != "":
                # Format key
                formatted_key = key.replace("_", " ").title()
                lines.append(f"• {formatted_key}: {value}")

        return "\n".join(lines) if lines else "No significant details."

    def _get_risk_color(self, risk_level: str) -> colors.Color:
        """Get color for risk level (ReportLab)"""
        level = risk_level.lower()
        if level == "critical":
            return colors.HexColor("#d32f2f")  # Dark red
        elif level == "high":
            return colors.HexColor("#f57c00")  # Orange
        elif level == "medium":
            return colors.HexColor("#fbc02d")  # Yellow
        else:
            return colors.HexColor("#689f38")  # Green

    def _get_risk_color_hex(self, risk_level: str) -> str:
        """Get hex color for risk level (HTML)"""
        level = risk_level.lower()
        if level == "critical":
            return "#d32f2f"
        elif level == "high":
            return "#f57c00"
        elif level == "medium":
            return "#fbc02d"
        else:
            return "#689f38"

    def _upload_to_azure_blob(self, content: Any, product_id: str, format: str) -> str:
        """Upload report to Azure Blob Storage and return SAS URL"""
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        blob_name = f"risk-reports/{product_id}/{timestamp}.{format}"

        # Check if Azure Blob Storage is configured
        azure_enabled = os.getenv("AZURE_BLOB_ENABLED", "false").lower() == "true"
        if not azure_enabled:
            logger.info(f"Azure Blob Storage disabled, returning local path for report: {product_id}")
            return f"/api/v1/risk/report/local/{product_id}/{timestamp}.{format}"

        try:
            # Upload based on format
            if format == "pdf":
                content_bytes = content.read() if hasattr(content, "read") else content
                self.storage_client.upload_file(
                    blob_name=blob_name,
                    file_data=content_bytes,
                    content_type="application/pdf",
                )
            elif format == "html":
                content_bytes = content.encode("utf-8") if isinstance(content, str) else content
                self.storage_client.upload_file(
                    blob_name=blob_name,
                    file_data=content_bytes,
                    content_type="text/html",
                )
            elif format == "json":
                content_bytes = content.encode("utf-8") if isinstance(content, str) else content
                self.storage_client.upload_file(
                    blob_name=blob_name,
                    file_data=content_bytes,
                    content_type="application/json",
                )

            # Generate SAS URL with 24 hour expiry
            url = self.storage_client.generate_sas_url(
                blob_name=blob_name,
                expiry_hours=24,
            )

            logger.info(f"Report uploaded to Azure Blob Storage: {blob_name}")
            return url

        except Exception as e:
            logger.warning(f"Azure Blob Storage upload failed: {e}")
            # Return local path as fallback
            return f"/api/v1/risk/report/local/{product_id}/{timestamp}.{format}"
