import logging
import os
import json
import hashlib
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from weasyprint import HTML
import markdown
from markdown.extensions import tables, fenced_code, nl2br, extra

logger = logging.getLogger(__name__)


@dataclass
class DocumentGenerationResult:
    """Structured result for document generation"""

    success: bool
    pdf_path: Optional[str] = None
    markdown_content: Optional[str] = None
    html_path: Optional[str] = None
    error_message: Optional[str] = None
    generation_time: Optional[float] = None
    file_hash: Optional[str] = None


class DocumentationAgentLogic:
    """
    Enhanced Documentation Agent for generating Prior Authorization reports
    and Letters of Medical Necessity with professional formatting
    """

    def __init__(self, agent_id: str, version: str = "2.0"):
        self.agent_id = agent_id
        self.version = version
        self.logger = logger

        # Directory setup
        self.base_dir = Path(__file__).parent
        self.templates_dir = self.base_dir / "templates"
        self.output_dir = self.base_dir.parent.parent / "_outputs_and_data" / "generated_reports"
        self.archive_dir = self.output_dir / "archive"

        # Create directories
        for directory in [self.output_dir, self.archive_dir, self.templates_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment with custom filters
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir), autoescape=True)
        self._register_custom_filters()

        # Configuration
        self.config = {
            "company_name": "CureViaX",
            "company_tagline": "Intelligent Biomedical Research, Verified by AI",
            "company_url": "https://www.cureviax.com",
            "company_email": "support@cureviax.com",
            "logo_filename": "cureviax_logo.png",
            "enable_watermark": True,
            "enable_qr_code": True,
            "max_file_size_mb": 10,
        }

        # Markdown extensions
        self.markdown_extensions = [
            "tables",
            "fenced_code",
            "nl2br",
            "extra",
            "toc",
            "attr_list",
            "md_in_html",
            "def_list",
        ]

        self.logger.info(
            f"DocumentationAgentLogic v{self.version} initialized for agent {self.agent_id}"
        )

    def _register_custom_filters(self):
        """Register custom Jinja2 filters"""
        self.jinja_env.filters["title_case"] = lambda x: str(x).title() if x else ""
        self.jinja_env.filters["percentage"] = lambda x: f"{float(x) * 100:.1f}%" if x else "0%"
        self.jinja_env.filters["round_percent"] = (
            lambda x: f"{round(float(x) * 100)}%" if x else "0%"
        )
        self.jinja_env.filters["date_format"] = (
            lambda x: datetime.strptime(x, "%Y-%m-%d").strftime("%B %d, %Y") if x else ""
        )
        self.jinja_env.filters["escape_html"] = (
            lambda x: str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if x
            else ""
        )
        # Add safe unicode filter
        self.jinja_env.filters["safe_unicode"] = lambda x: self._safe_unicode_str(x)

    def _safe_unicode_str(self, text):
        """Safely convert text to string, handling unicode"""
        if text is None:
            return ""
        try:
            # Convert to string and encode/decode to handle unicode
            return str(text).encode("utf-8", errors="replace").decode("utf-8")
        except:
            # Fallback to ASCII representation
            return str(text).encode("ascii", errors="replace").decode("ascii")

    def _console_safe_str(self, text):
        """Convert text to console-safe ASCII string"""
        if text is None:
            return ""
        return str(text).encode("ascii", errors="replace").decode("ascii")

    def process_task(self, task_payload: dict) -> dict:
        """Enhanced main entry point for generating documentation"""
        start_time = datetime.now()

        # Log incoming data structure for debugging
        self.logger.debug(f"Incoming task_payload keys: {list(task_payload.keys())}")

        # Extract and normalize data
        try:
            normalized_data = self._normalize_input_data(task_payload)
            report_data = normalized_data["report_data"]
            original_request = normalized_data["original_request"]
            workflow_id = normalized_data["workflow_id"]
            report_type = normalized_data["report_type"]
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to normalize input data: {str(e)}",
                "agent_id": self.agent_id,
            }

        # Validate normalized inputs
        validation_result = self._validate_normalized_inputs(report_data, original_request)
        if not validation_result["valid"]:
            return {
                "status": "error",
                "message": validation_result["message"],
                "agent_id": self.agent_id,
            }

        self.logger.info(
            f"Generating documentation for workflow '{workflow_id}' of type '{report_type}'"
        )

        try:
            results = {}

            # Generate PDF report
            pdf_result = self._build_pa_summary_pdf(
                report_data, original_request, workflow_id, report_type
            )
            results["pdf_generation"] = asdict(pdf_result)

            # Generate Markdown letter
            md_result = self._build_necessity_letter_md(report_data, original_request, workflow_id)
            results["markdown_generation"] = asdict(md_result)

            # Generate HTML preview if requested
            if task_payload.get("generate_html_preview", False):
                html_result = self._build_html_preview(report_data, original_request, workflow_id)
                results["html_generation"] = asdict(html_result)

            # Calculate total generation time
            generation_time = (datetime.now() - start_time).total_seconds()

            # Archive if requested
            if task_payload.get("archive", True):
                self._archive_documents(results, workflow_id)

            return {
                "status": "success",
                "outputs": {
                    "summary_pdf_path": pdf_result.pdf_path,
                    "necessity_letter_md": self._console_safe_str(md_result.markdown_content),
                    "html_preview_path": results.get("html_generation", {}).get("html_path"),
                    "generation_results": results,
                },
                "message": "Documentation generated successfully",
                "generation_time_seconds": generation_time,
                "agent_id": self.agent_id,
                "workflow_id": workflow_id,
            }

        except Exception as e:
            self.logger.error(f"Failed to generate documentation: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Documentation generation failed: {str(e)}",
                "agent_id": self.agent_id,
                "workflow_id": workflow_id,
            }

    def _normalize_input_data(self, task_payload: dict) -> dict:
        """Normalize input data to handle various structures"""
        # Extract base data
        workflow_id = task_payload.get(
            "workflow_id", f"WF_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        report_type = task_payload.get("report_type", "prior_authorization")

        # Initialize report_data and original_request
        report_data = {}
        original_request = {}

        # First, check if report_data is a string reference
        report_data_field = task_payload.get("report_data", {})
        if isinstance(report_data_field, str) and report_data_field.startswith("RESULT_FROM_"):
            self.logger.info(
                f"Found workflow reference: {report_data_field}, looking for actual data in payload"
            )

        # Extract original_request from various possible locations
        if "original_request" in task_payload and isinstance(
            task_payload["original_request"], dict
        ):
            original_request = task_payload["original_request"]
        elif "data" in task_payload and isinstance(task_payload["data"], dict):
            # Sometimes original request is nested under 'data'
            original_request = task_payload["data"]

        # Look for the actual prediction data in the task payload
        # Based on the logs, the data appears to be directly in the task_payload
        prediction_fields = {
            "decision": None,
            "confidence": None,
            "clinical_rationale": None,
            "supporting_evidence": None,
            "identified_gaps": None,
            "key_factors": None,
        }

        # Extract prediction data from task_payload
        for field in prediction_fields:
            if field in task_payload:
                prediction_fields[field] = task_payload[field]

        # Also check for nested structures
        for key in ["result", "prediction", "step6_result", "approval_prediction"]:
            if key in task_payload and isinstance(task_payload[key], dict):
                for field in prediction_fields:
                    if field in task_payload[key] and prediction_fields[field] is None:
                        prediction_fields[field] = task_payload[key][field]

        # Map to standard field names
        report_data = {
            "decision_prediction": prediction_fields["decision"] or "Unknown",
            "confidence_score": prediction_fields["confidence"],
            "clinical_rationale": prediction_fields["clinical_rationale"]
            or "No rationale provided",
            "supporting_evidence": prediction_fields["supporting_evidence"] or [],
            "identified_gaps": prediction_fields["identified_gaps"] or [],
            "key_factors": prediction_fields["key_factors"] or [],
        }

        # Add any additional fields from task_payload that might be relevant
        additional_fields = [
            "patient_history",
            "drug_name",
            "diagnosis_codes",
            "patient_id",
            "insurer_id",
        ]
        for field in additional_fields:
            if field in task_payload:
                report_data[field] = task_payload[field]

        # If original_request is still empty, extract from task_payload
        if not original_request:
            original_request = {
                "patient_id": task_payload.get("patient_id", "Unknown"),
                "drug_name": task_payload.get("drug_name", "Unknown"),
                "diagnosis_codes": task_payload.get("diagnosis_codes", []),
                "provider_name": task_payload.get("provider_name", "Healthcare Provider"),
                "provider_npi": task_payload.get("provider_npi", "0000000000"),
                "insurer_id": task_payload.get("insurer_id", "Unknown"),
            }

        # Clean up any unicode issues in the data
        report_data = self._clean_unicode_dict(report_data)
        original_request = self._clean_unicode_dict(original_request)

        # Log normalized structure
        self.logger.debug(f"Normalized report_data keys: {list(report_data.keys())}")
        self.logger.debug(
            f"Decision: {report_data.get('decision_prediction')}, Confidence: {report_data.get('confidence_score')}"
        )

        return {
            "report_data": report_data,
            "original_request": original_request,
            "workflow_id": workflow_id,
            "report_type": report_type,
        }

    def _clean_unicode_dict(self, data: dict) -> dict:
        """Clean unicode characters from dictionary to prevent encoding errors"""
        if not isinstance(data, dict):
            return data

        cleaned = {}
        for key, value in data.items():
            if isinstance(value, str):
                cleaned[key] = self._safe_unicode_str(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    self._safe_unicode_str(item) if isinstance(item, str) else item
                    for item in value
                ]
            elif isinstance(value, dict):
                cleaned[key] = self._clean_unicode_dict(value)
            else:
                cleaned[key] = value
        return cleaned

    def _validate_normalized_inputs(self, report_data: dict, original_request: dict) -> dict:
        """Validate normalized input data"""
        if not report_data:
            return {"valid": False, "message": "Empty report_data after normalization"}

        # Check for required fields with more flexibility
        required_fields = ["decision_prediction", "clinical_rationale"]
        missing_fields = []

        for field in required_fields:
            if (
                field not in report_data
                or report_data[field] is None
                or str(report_data[field]).strip() == ""
            ):
                missing_fields.append(field)

        if missing_fields:
            # Log what we actually have for debugging
            self.logger.warning(f"Missing required fields: {missing_fields}")
            self.logger.warning(f"Available fields in report_data: {list(report_data.keys())}")

            # Try to provide helpful error message
            return {
                "valid": False,
                "message": f"Missing required fields in report_data: {', '.join(missing_fields)}. Available fields: {', '.join(report_data.keys())}",
            }

        return {"valid": True, "message": "Validation passed"}

    def _build_pa_summary_pdf(
        self,
        prediction_data: dict,
        original_request: dict,
        workflow_id: str,
        report_type: str = "prior_authorization",
    ) -> DocumentGenerationResult:
        """Enhanced PDF generation with better error handling and features"""
        try:
            start_time = datetime.now()

            # Select template based on report type
            template_name = f"{report_type}_template.html"
            if template_name not in self.jinja_env.list_templates():
                template_name = "pa_summary_template.html"  # Fallback

            # Create default template if none exists
            if template_name not in self.jinja_env.list_templates():
                self._create_default_template()
                template_name = "pa_summary_template.html"

            template = self.jinja_env.get_template(template_name)

            # Build logo path
            logo_path = self._get_logo_path()

            # Extract and format decision
            decision = str(prediction_data.get("decision_prediction", "")).lower()
            is_approved = decision in ["approve", "approved", "yes", "true", "1"]

            # Prepare enhanced context - ensure all strings are unicode-safe
            context = {
                "prediction_data": prediction_data,
                "report_data": original_request,
                "report_date": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
                "workflow_id": workflow_id,
                "agent_id": self.agent_id,
                "agent_version": self.version,
                "logo_path": logo_path,
                "company": self.config,
                "generation_timestamp": datetime.now().isoformat(),
                # Additional context for enhanced reporting
                "drug_name_formatted": self._safe_unicode_str(
                    original_request.get("drug_name", "N/A")
                ).title(),
                "patient_id_masked": self._mask_patient_id(original_request.get("patient_id", "")),
                "insurer_name": self._get_insurer_name(original_request.get("insurer_id", "")),
                "diagnosis_codes_formatted": ", ".join(
                    [
                        self._safe_unicode_str(code)
                        for code in original_request.get("diagnosis_codes", [])
                    ]
                ),
                "provider_name": self._safe_unicode_str(
                    original_request.get("provider_name", "Healthcare Provider")
                ),
                "is_approved": is_approved,
                "decision_formatted": "APPROVED" if is_approved else "DENIED",
                "confidence_percentage": self._format_confidence(
                    prediction_data.get("confidence_score")
                ),
                "report_metadata": {
                    "total_evidence": len(prediction_data.get("supporting_evidence", [])),
                    "total_gaps": len(prediction_data.get("identified_gaps", [])),
                    "has_approval": is_approved,
                    "workflow_stage": prediction_data.get("workflow_stage", "Final Review"),
                },
            }

            # Render HTML
            html_string = template.render(context)

            # Generate filename
            decision_text = "Approved" if is_approved else "Denied"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"PA_Summary_{decision_text}_{workflow_id[:8]}_{timestamp}.pdf"
            pdf_filepath = self.output_dir / pdf_filename

            # Generate PDF with WeasyPrint
            HTML(string=html_string, base_url=str(self.base_dir)).write_pdf(
                pdf_filepath,
                stylesheets=[self._get_print_stylesheet()]
                if self._get_print_stylesheet()
                else None,
            )

            # Calculate file hash
            file_hash = self._calculate_file_hash(pdf_filepath)

            # Verify file size
            file_size_mb = pdf_filepath.stat().st_size / (1024 * 1024)
            if file_size_mb > self.config["max_file_size_mb"]:
                self.logger.warning(f"Generated PDF exceeds size limit: {file_size_mb:.2f}MB")

            generation_time = (datetime.now() - start_time).total_seconds()

            self.logger.info(
                f"Generated PA Summary PDF at: {pdf_filepath} (Size: {file_size_mb:.2f}MB)"
            )

            return DocumentGenerationResult(
                success=True,
                pdf_path=str(pdf_filepath),
                generation_time=generation_time,
                file_hash=file_hash,
            )

        except TemplateNotFound as e:
            error_msg = f"Template not found: {e}"
            self.logger.error(error_msg)
            return DocumentGenerationResult(success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"PDF generation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return DocumentGenerationResult(success=False, error_message=error_msg)

    def _build_necessity_letter_md(
        self, prediction_data: dict, original_request: dict, workflow_id: str
    ) -> DocumentGenerationResult:
        """Enhanced Markdown letter generation with professional formatting"""
        try:
            patient_id = original_request.get("patient_id", "Unknown")
            drug_name = self._safe_unicode_str(original_request.get("drug_name", "Unknown"))
            provider_name = self._safe_unicode_str(
                original_request.get("provider_name", "Dr. Smith")
            )
            provider_npi = original_request.get("provider_npi", "1234567890")
            diagnosis_codes = original_request.get("diagnosis_codes", ["E11.9"])

            # Determine approval status
            decision = str(prediction_data.get("decision_prediction", "")).lower()
            is_approved = decision in ["approve", "approved", "yes", "true", "1"]

            # Build professional letter
            md_parts = [
                "# Letter of Medical Necessity",
                "",
                f"**Date:** {datetime.now().strftime('%B %d, %Y')}",
                "",
                "**To:** Prior Authorization Department",
                f"**From:** {provider_name}, MD",
                f"**NPI:** {provider_npi}",
                "",
                f"**Patient ID:** {self._mask_patient_id(patient_id)}",
                f"**Diagnosis Codes:** {', '.join([self._safe_unicode_str(code) for code in diagnosis_codes])}",
                "",
                f"**RE:** Prior Authorization Request for {drug_name.title()}",
                "",
                "---",
                "",
                "To Whom It May Concern,",
                "",
                f"I am writing to request prior authorization for **{drug_name.title()}** for the above-referenced patient. "
                f"This medication is medically necessary for the treatment of the patient's condition.",
                "",
                "## Clinical Assessment",
                "",
                "Based on comprehensive clinical review and current evidence-based guidelines, the following assessment has been made:",
                "",
                "**Clinical Rationale:**",
                f"> {self._safe_unicode_str(prediction_data.get('clinical_rationale', 'Clinical rationale not provided'))}",
                "",
            ]

            # Add confidence score if available
            confidence_score = prediction_data.get("confidence_score")
            if confidence_score is not None:
                md_parts.extend(
                    [
                        f"**Assessment Confidence:** {self._format_confidence(confidence_score)}",
                        "",
                    ]
                )

            # Add supporting evidence
            supporting_evidence = prediction_data.get("supporting_evidence", [])
            if supporting_evidence:
                md_parts.extend(
                    [
                        "## Supporting Clinical Evidence",
                        "",
                        "The following clinical factors support this request:",
                        "",
                    ]
                )
                for i, evidence in enumerate(supporting_evidence, 1):
                    md_parts.append(f"{i}. {self._safe_unicode_str(evidence)}")
                md_parts.append("")

            # Add decision-specific content
            if is_approved:
                md_parts.extend(
                    [
                        "## Recommendation",
                        "",
                        "Based on the clinical assessment, this patient **meets all necessary criteria** for approval "
                        "as per established coverage policies and clinical guidelines. The prescribed medication is "
                        "appropriate for the patient's condition and represents optimal therapy.",
                        "",
                    ]
                )
            else:
                # Add identified gaps
                gaps = prediction_data.get("identified_gaps", [])
                if gaps:
                    md_parts.extend(
                        [
                            "## Areas Requiring Additional Documentation",
                            "",
                            "The following items may require clarification or additional documentation:",
                            "",
                        ]
                    )
                    for gap in gaps:
                        md_parts.append(f"- {self._safe_unicode_str(gap)}")
                    md_parts.append("")

                md_parts.extend(
                    [
                        "## Next Steps",
                        "",
                        "To proceed with this authorization request, please provide the additional documentation "
                        "outlined above. I am available to discuss this case further if needed.",
                        "",
                    ]
                )

            # Add patient safety considerations if any
            if original_request.get("allergies") or original_request.get("contraindications"):
                md_parts.extend(
                    [
                        "## Patient Safety Considerations",
                        "",
                    ]
                )
                if original_request.get("allergies"):
                    md_parts.append(
                        f"**Known Allergies:** {', '.join([self._safe_unicode_str(a) for a in original_request['allergies']])}"
                    )
                if original_request.get("contraindications"):
                    md_parts.append("**Contraindications Reviewed:** Yes")
                md_parts.append("")

            # Add closing
            md_parts.extend(
                [
                    "## Conclusion",
                    "",
                    f"I respectfully request {'approval' if is_approved else 'consideration'} of **{drug_name.title()}** for this patient. "
                    "This medication is medically necessary and appropriate based on current clinical guidelines "
                    "and the patient's specific medical condition.",
                    "",
                    "Should you require any additional information or documentation, please do not hesitate to contact my office.",
                    "",
                    "Thank you for your prompt consideration of this request.",
                    "",
                    "Sincerely,",
                    "",
                    f"**{provider_name}, MD**",
                    "",
                    "---",
                    "",
                    f"*Generated by CureViaX PA Intelligence System v{self.version}*",
                    f"*Workflow ID: {workflow_id}*",
                    f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*",
                ]
            )

            markdown_content = "\n".join(md_parts)

            # Save markdown file with UTF-8 encoding
            md_filename = (
                f"Letter_of_Necessity_{workflow_id[:8]}_{datetime.now().strftime('%Y%m%d')}.md"
            )
            md_filepath = self.output_dir / md_filename

            with open(md_filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            self.logger.info(f"Generated Letter of Medical Necessity at: {md_filepath}")

            return DocumentGenerationResult(
                success=True,
                markdown_content=markdown_content,
                html_path=str(md_filepath),
            )

        except Exception as e:
            error_msg = f"Markdown generation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return DocumentGenerationResult(success=False, error_message=error_msg)

    def _build_html_preview(
        self, report_data: dict, original_request: dict, workflow_id: str
    ) -> DocumentGenerationResult:
        """Generate HTML preview of the markdown letter"""
        try:
            # Get markdown content
            md_result = self._build_necessity_letter_md(report_data, original_request, workflow_id)

            if not md_result.success:
                return md_result

            # Convert markdown to HTML
            html_content = markdown.markdown(
                md_result.markdown_content, extensions=self.markdown_extensions
            )

            # Wrap in HTML template with enhanced styling
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Letter of Medical Necessity - {workflow_id}</title>
                <style>
                    body {{
                        font-family: 'Helvetica Neue', Arial, sans-serif;
                        max-width: 800px;
                        margin: 40px auto;
                        padding: 20px;
                        line-height: 1.6;
                        color: #333;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        background-color: white;
                        padding: 40px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    h1, h2 {{
                        color: #1a237e;
                        margin-top: 30px;
                    }}
                    h1 {{
                        border-bottom: 2px solid #3949ab;
                        padding-bottom: 10px;
                    }}
                    blockquote {{
                        border-left: 4px solid #3949ab;
                        padding-left: 20px;
                        margin-left: 0;
                        font-style: italic;
                        background-color: #f8f9fa;
                        padding: 15px 20px;
                        border-radius: 4px;
                    }}
                    strong {{
                        color: #1a237e;
                    }}
                    hr {{
                        border: none;
                        border-top: 1px solid #e0e0e0;
                        margin: 30px 0;
                    }}
                    ul, ol {{
                        margin-left: 20px;
                    }}
                    li {{
                        margin-bottom: 8px;
                    }}
                    @media print {{
                        body {{
                            background-color: white;
                        }}
                        .container {{
                            box-shadow: none;
                            padding: 0;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    {html_content}
                </div>
            </body>
            </html>
            """

            # Save HTML file with UTF-8 encoding
            html_filename = f"Letter_Preview_{workflow_id[:8]}.html"
            html_filepath = self.output_dir / html_filename

            with open(html_filepath, "w", encoding="utf-8") as f:
                f.write(html_template)

            return DocumentGenerationResult(success=True, html_path=str(html_filepath))

        except Exception as e:
            return DocumentGenerationResult(
                success=False, error_message=f"HTML preview generation failed: {str(e)}"
            )

    def _create_default_template(self):
        """Create a default PA summary template if none exists"""
        default_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Prior Authorization Summary - {{ workflow_id }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            line-height: 1.6;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo {
            max-width: 200px;
            margin-bottom: 20px;
        }
        h1 {
            color: #1a237e;
            margin-bottom: 10px;
        }
        .decision-box {
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            text-align: center;
        }
        .approved {
            background-color: #e8f5e9;
            border: 2px solid #4caf50;
            color: #2e7d32;
        }
        .denied {
            background-color: #ffebee;
            border: 2px solid #f44336;
            color: #c62828;
        }
        .section {
            margin: 30px 0;
        }
        .metadata {
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 4px;
            margin-top: 30px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="header">
        {% if logo_path %}
        <img src="{{ logo_path }}" alt="{{ company.company_name }}" class="logo">
        {% endif %}
        <h1>Prior Authorization Summary Report</h1>
        <p>{{ company.company_tagline }}</p>
    </div>

    <div class="decision-box {% if is_approved %}approved{% else %}denied{% endif %}">
        <h2>Decision: {{ decision_formatted }}</h2>
        {% if confidence_percentage %}
        <p>Confidence: {{ confidence_percentage }}</p>
        {% endif %}
    </div>

    <div class="section">
        <h2>Request Information</h2>
        <table>
            <tr>
                <th>Field</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Patient ID</td>
                <td>{{ patient_id_masked }}</td>
            </tr>
            <tr>
                <td>Drug Name</td>
                <td>{{ drug_name_formatted|safe_unicode }}</td>
            </tr>
            <tr>
                <td>Provider</td>
                <td>{{ provider_name|safe_unicode }}</td>
            </tr>
            <tr>
                <td>Diagnosis Codes</td>
                <td>{{ diagnosis_codes_formatted|safe_unicode }}</td>
            </tr>
            <tr>
                <td>Insurer</td>
                <td>{{ insurer_name }}</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <h2>Clinical Rationale</h2>
        <p>{{ prediction_data.clinical_rationale|safe_unicode }}</p>
    </div>

    {% if prediction_data.supporting_evidence %}
    <div class="section">
        <h2>Supporting Evidence</h2>
        <ul>
        {% for evidence in prediction_data.supporting_evidence %}
            <li>{{ evidence|safe_unicode }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if prediction_data.identified_gaps %}
    <div class="section">
        <h2>Identified Gaps</h2>
        <ul>
        {% for gap in prediction_data.identified_gaps %}
            <li>{{ gap|safe_unicode }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}

    <div class="metadata">
        <p><strong>Report Generated:</strong> {{ report_date }}</p>
        <p><strong>Workflow ID:</strong> {{ workflow_id }}</p>
        <p><strong>Generated by:</strong> {{ company.company_name }} PA Intelligence System v{{ agent_version }}</p>
    </div>
</body>
</html>
"""
        template_path = self.templates_dir / "pa_summary_template.html"
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(default_template.strip())
        self.logger.info(f"Created default template at {template_path}")

    def _format_confidence(self, confidence_score: Any) -> str:
        """Format confidence score as percentage"""
        if confidence_score is None:
            return "N/A"
        try:
            score = float(confidence_score)
            if 0 <= score <= 1:
                return f"{score * 100:.1f}%"
            else:
                return f"{score:.1f}%"
        except (ValueError, TypeError):
            return str(confidence_score)

    def _get_logo_path(self) -> str:
        """Get the logo file path with fallback options"""
        logo_locations = [
            self.base_dir.parent.parent.parent / "branding" / self.config["logo_filename"],
            self.base_dir.parent.parent / "branding" / self.config["logo_filename"],
            self.base_dir / "assets" / self.config["logo_filename"],
        ]

        for path in logo_locations:
            if path.exists():
                return path.as_uri()

        # Return placeholder if no logo found
        self.logger.warning("Logo file not found in expected locations")
        return "https://via.placeholder.com/180x60?text=CureViaX"

    def _get_print_stylesheet(self) -> Optional[str]:
        """Get print-specific stylesheet if available"""
        stylesheet_path = self.templates_dir / "print_styles.css"
        if stylesheet_path.exists():
            return str(stylesheet_path)
        return None

    def _mask_patient_id(self, patient_id: str) -> str:
        """Mask patient ID for privacy"""
        if not patient_id or len(patient_id) < 4:
            return "****"
        patient_id = self._safe_unicode_str(patient_id)
        return f"{patient_id[:2]}****{patient_id[-2:]}"

    def _get_insurer_name(self, insurer_id: str) -> str:
        """Get human-readable insurer name"""
        insurer_map = {
            "TEST-INS": "Test Insurance Co.",
            "BCBS": "Blue Cross Blue Shield",
            "UHC": "UnitedHealthcare",
            "AETNA": "Aetna",
            "CIGNA": "Cigna",
            "HUMANA": "Humana",
            "ANTHEM": "Anthem",
            "KAISER": "Kaiser Permanente",
        }
        return insurer_map.get(insurer_id, self._safe_unicode_str(insurer_id))

    def _calculate_file_hash(self, filepath: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _archive_documents(self, results: dict, workflow_id: str):
        """Archive generated documents with enhanced metadata"""
        try:
            archive_subdir = self.archive_dir / datetime.now().strftime("%Y%m")
            archive_subdir.mkdir(exist_ok=True)

            # Save metadata with UTF-8 encoding
            metadata_file = archive_subdir / f"{workflow_id}_metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "workflow_id": workflow_id,
                        "generated_at": datetime.now().isoformat(),
                        "agent_id": self.agent_id,
                        "agent_version": self.version,
                        "results": results,
                        "system_info": {
                            "platform": platform.system(),
                            "python_version": platform.python_version(),
                        },
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            self.logger.info(f"Archived documentation metadata to {metadata_file}")

        except Exception as e:
            self.logger.error(f"Failed to archive documents: {e}")

    async def shutdown(self):
        """Cleanup resources"""
        self.logger.info(f"DocumentationAgentLogic shutting down for agent {self.agent_id}")
