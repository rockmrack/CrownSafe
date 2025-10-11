# report_builder_agent_01/logic.py
# Version: 2.1-PA-ENHANCED - Enhanced with Prior Authorization report capability

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import os
import base64
import uuid
from enum import Enum
from dataclasses import asdict
from collections import Counter
from pathlib import Path

try:
    import markdown

    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    markdown = None

try:
    from xhtml2pdf import pisa

    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False
    pisa = None

try:
    # Optional high-fidelity HTML renderer
    from weasyprint import HTML as WEASY_HTML, CSS as WEASY_CSS  # type: ignore

    WEASYPRINT_AVAILABLE = True
except Exception:
    WEASYPRINT_AVAILABLE = False
    WEASY_HTML = None  # type: ignore
    WEASY_CSS = None  # type: ignore

try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None

try:
    import qrcode

    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    qrcode = None

try:
    from jinja2 import Environment, FileSystemLoader

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    Environment = None
    FileSystemLoader = None

# ====== Configuration ======
COMPANY_NAME = "CureViaX"
TAGLINE = "Intelligent Biomedical Research, Verified by AI"
CONTACT_EMAIL = "support@cureviax.com"
COMPANY_URL = "https://www.cureviax.com"
REPORTS_OUTPUT_DIR = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
    "generated_reports",
)
LOGO_PATH = "C:/Users/rossd/Downloads/RossNetAgents/branding/cureviax_logo.png"

# CRITICAL: Define templates directory relative to this file
TEMPLATES_DIR = Path(__file__).parent / "templates"

logger_rb_logic_default = logging.getLogger(__name__)

# Create output directory if it doesn't exist
if not os.path.exists(REPORTS_OUTPUT_DIR):
    try:
        os.makedirs(REPORTS_OUTPUT_DIR)
        logger_rb_logic_default.info(
            f"Created reports output directory: {REPORTS_OUTPUT_DIR}"
        )
    except Exception as e_mkdir:
        logger_rb_logic_default.error(
            f"Failed to create reports output directory {REPORTS_OUTPUT_DIR}: {e_mkdir}",
            exc_info=True,
        )
        REPORTS_OUTPUT_DIR = os.path.abspath(os.path.dirname(__file__))
        logger_rb_logic_default.warning(
            f"Falling back to report output directory: {REPORTS_OUTPUT_DIR}"
        )

# Create templates directory if it doesn't exist
if not TEMPLATES_DIR.exists():
    try:
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        logger_rb_logic_default.info(f"Created templates directory: {TEMPLATES_DIR}")
    except Exception as e:
        logger_rb_logic_default.error(
            f"Failed to create templates directory: {e}", exc_info=True
        )


class MessageType(Enum):
    TASK_ASSIGN = "TASK_ASSIGN"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_FAIL = "TASK_FAIL"
    DISCOVERY_ACK = "DISCOVERY_ACK"
    PONG = "PONG"


# --- Utilities ---
def escape_html(text):
    import html

    return html.escape(str(text)) if text else ""


def html_img_tag(path, width=180, style="margin-bottom:18px;"):
    local_url = "file:///" + path.replace("\\", "/")
    return (
        f'<img src="{local_url}" width="{width}" style="{style}" alt="CureViaX Logo">'
    )


def markdown_to_html(md):
    return markdown.markdown(
        md,
        extensions=[
            "tables",
            "fenced_code",
            "sane_lists",
            "nl2br",
            "extra",
            "toc",
            "attr_list",
            "md_in_html",
            "def_list",
        ],
    )


def generate_adverse_event_chart(top_reactions, output_dir, basename):
    if (
        not top_reactions
        or not isinstance(top_reactions, list)
        or len(top_reactions) == 0
    ):
        return None
    try:
        labels = [
            r.get("term") or r.get("reaction") or "Unknown" for r in top_reactions
        ][:10]
        counts = [int(r.get("count", 0)) for r in top_reactions][:10]
        fig, ax = plt.subplots(figsize=(6, 3))
        _ = ax.bar(
            labels, counts, color="#3071B8", alpha=0.85
        )  # bars (reserved for future styling)
        ax.set_title("Top Adverse Reactions (openFDA)", fontsize=13, weight="bold")
        ax.set_xlabel("Reaction")
        ax.set_ylabel("Number of Reports")
        plt.xticks(rotation=22, ha="right")
        plt.tight_layout()
        chart_path = os.path.join(output_dir, f"{basename}_ae_chart.png")
        plt.savefig(chart_path, dpi=150)
        plt.close(fig)
        return chart_path
    except Exception as e:
        logger_rb_logic_default.error(
            f"Failed to generate AE chart: {e}", exc_info=True
        )
        return None


def generate_qr_code(data: str, output_dir: str, basename: str) -> Optional[str]:
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=3,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        qr_path = os.path.join(output_dir, f"{basename}_qr.png")
        img.save(qr_path)
        return qr_path
    except Exception as e:
        logger_rb_logic_default.error(f"Failed to generate QR code: {e}", exc_info=True)
        return None


# --- Section Formatters for Research Reports ---


def format_highlights(pubmed_articles, trials, adverse_events):
    n = len(pubmed_articles.get("articles", [])) if pubmed_articles else 0
    t = len(trials.get("trials_data", [])) if trials else 0
    aecount = (
        len(adverse_events.get("top_adverse_reactions", [])) if adverse_events else 0
    )
    return f"""
    <div style="background:#f6fbff;border:1.5px solid #bee1fa;padding:10px 18px 8px 18px;border-radius:9px;display:flex;flex-direction:row;justify-content:space-between;margin:12px 0 18px 0;font-size:12pt;">
        <div><b>Articles:</b> {n}</div>
        <div><b>Trials:</b> {t}</div>
        <div><b>Top AE Reactions:</b> {aecount}</div>
    </div>
    """


def format_executive_summary(pubmed_articles, trials, adverse_events):
    n = len(pubmed_articles.get("articles", [])) if pubmed_articles else 0
    t = len(trials.get("trials_data", [])) if trials else 0
    aecount = (
        len(adverse_events.get("top_adverse_reactions", [])) if adverse_events else 0
    )
    return f"""
    <a name='executive_summary'></a>
    <h1>Executive Summary</h1>
    <p>
    This evidence report summarises findings on the efficacy and safety of the queried intervention, using structured data from PubMed (n={n} studies), ClinicalTrials.gov (n={t} trials), and openFDA (n={aecount} top adverse reactions). Please refer to each section for a detailed, source-linked analysis.
    </p>
    """


def format_background(goal, drug, disease):
    disease_line = f"<b>Disease Context:</b> {escape_html(disease)}." if disease else ""
    drug_line = f"<b>Drug:</b> {escape_html(drug)}." if drug else ""
    if not disease_line and not drug_line:
        disease_drug_block = ""
    else:
        disease_drug_block = f"{disease_line} {drug_line}"
    return f"""
    <a name="background"></a>
    <h1>Background & Context</h1>
    <p><b>Research Goal:</b> {escape_html(goal)}</p>
    <p>{disease_drug_block}</p>
    <p>This report was prepared by the CureViaX platform, leveraging AI-powered biomedical research and validated data sources.</p>
    """


def format_methods():
    return f"""
    <a name="methods"></a>
    <h1>Methods</h1>
    <ul>
    <li><b>PubMed:</b> AI-driven literature search for the specified drug/disease.</li>
    <li><b>ClinicalTrials.gov:</b> Filtered for condition/intervention.</li>
    <li><b>openFDA:</b> Top adverse event reports for the drug.</li>
    <li>All data as of: <b>{datetime.now(timezone.utc).strftime("%Y-%m-%d")}</b></li>
    </ul>
    """


def format_pubmed_articles(pubmed_data):
    if not pubmed_data or not isinstance(pubmed_data, dict):
        return "<h2>Literature Review</h2><p>No PubMed data available.</p>"
    articles = pubmed_data.get("articles", [])
    q_used = pubmed_data.get("query_used_for_api", "N/A")
    out = [
        '<a name="literature"></a>',
        "<h1>2. Literature Review</h1>",
        f"<p><b>Query Used:</b> <i>{escape_html(q_used)}</i></p>",
        "<table border='1' style='font-size:10pt; margin-bottom:1em;'><thead><tr>"
        "<th>PMID</th><th>Title</th><th>Authors</th><th>Journal (Date)</th></tr></thead><tbody>",
    ]
    if not articles:
        out.append(
            "<tr><td colspan='4'>No articles found for these search criteria.</td></tr>"
        )
    else:
        for art in articles:
            a = art if isinstance(art, dict) else asdict(art)
            pmid = a.get("pmid", "N/A")
            pmid_html = (
                f'<a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/">{pmid}</a>'
                if pmid and pmid != "N/A"
                else pmid
            )
            title = escape_html(a.get("title", "N/A"))
            authors = ", ".join(a.get("authors", [])) if a.get("authors") else "N/A"
            journal = escape_html(a.get("journal", "N/A"))
            pub_date = escape_html(a.get("publication_date", "N/A"))
            out.append(
                f"<tr><td>{pmid_html}</td><td>{title}</td><td>{authors}</td><td>{journal} ({pub_date})</td></tr>"
            )
            if a.get("abstract"):
                out.append(
                    f'<tr><td colspan="4"><div style="font-size:9pt;"><b>Abstract:</b> {escape_html(a["abstract"])}</div></td></tr>'
                )
    out.append("</tbody></table>")
    return "\n".join(out)


def format_clinical_trials(trials_data):
    if not trials_data or not isinstance(trials_data, dict):
        return "<h1>3. Clinical Trials</h1><p>No clinical trial data found.</p>"
    trials = trials_data.get("trials_data", [])
    out = [
        '<a name="trials"></a>',
        "<h1>3. Clinical Trials</h1>",
        "<table border='1' style='font-size:10pt; margin-bottom:1em;'><thead><tr>"
        "<th>NCT ID</th><th>Title</th><th>Status</th><th>Condition</th><th>Intervention</th></tr></thead><tbody>",
    ]
    if not trials:
        out.append("<tr><td colspan='5'>No clinical trials available.</td></tr>")
    else:
        for t in trials:
            tr = t if isinstance(t, dict) else asdict(t)
            nct = tr.get("nct_id", "N/A")
            nct_html = (
                f'<a href="{tr.get("url", "#")}" target="_blank">{nct}</a>'
                if nct and nct != "N/A"
                else nct
            )
            title = escape_html(tr.get("title", "N/A"))
            status = escape_html(tr.get("status", "N/A"))
            condition = escape_html(tr.get("condition", "N/A"))
            intervention = escape_html(tr.get("intervention", "N/A"))
            out.append(
                f"<tr><td>{nct_html}</td><td>{title}</td><td>{status}</td><td>{condition}</td><td>{intervention}</td></tr>"
            )
    out.append("</tbody></table>")
    return "\n".join(out)


def format_adverse_events(safety_data, chart_path=None):
    out = ['<a name="adverse_events"></a>', "<h1>4. Drug Safety Profile</h1>"]
    if chart_path and os.path.exists(chart_path):
        out.append(
            html_img_tag(
                chart_path, width=360, style="margin-bottom:22px; margin-top:12px;"
            )
        )
    top_reactions = safety_data.get("top_adverse_reactions", []) if safety_data else []
    if not top_reactions:
        out.append("<p>No adverse event data available.</p>")
    else:
        out.append(
            "<table border='1' style='font-size:10pt;'><thead><tr><th>Adverse Event</th><th>Report Count</th></tr></thead><tbody>"
        )
        for r in top_reactions:
            rname = escape_html(r.get("term", r.get("reaction", "N/A")))
            rcnt = escape_html(r.get("count", "N/A"))
            out.append(f"<tr><td>{rname}</td><td>{rcnt}</td></tr>")
        out.append("</tbody></table>")
    return "\n".join(out)


def format_references(pubmed_data, trials_data):
    refs = [
        '<a name="references"></a>',
        "<h1>References</h1>",
        '<ul style="font-size:9.5pt;">',
    ]
    if pubmed_data and isinstance(pubmed_data, dict):
        for a in pubmed_data.get("articles", []):
            pmid = a.get("pmid", "N/A")
            title = escape_html(a.get("title", "N/A"))
            if pmid and pmid != "N/A":
                refs.append(
                    f'<li>PubMed: <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/">{title} (PMID: {pmid})</a></li>'
                )
    if trials_data and isinstance(trials_data, dict):
        for t in trials_data.get("trials_data", []):
            nct = t.get("nct_id", "N/A")
            title = escape_html(t.get("title", "N/A"))
            url = t.get("url", "#")
            if nct and nct != "N/A":
                refs.append(
                    f'<li>ClinicalTrials.gov: <a href="{url}">{title} (NCT: {nct})</a></li>'
                )
    refs.append("</ul>")
    return "\n".join(refs)


def format_disclaimer():
    return """
    <a name="disclaimer"></a>
    <h1>Disclaimer & Contact</h1>
    <div style="font-size:9pt; color:#707070;">
    This report is AI-generated for informational purposes only. Not a substitute for medical advice. Contact: <a href="mailto:support@cureviax.com">support@cureviax.com</a> or <a href="https://www.cureviax.com">cureviax.com</a>.
    </div>
    """


def format_metadata(agent_id, version, dt_str, workflow_id, pdf_path, pubmed, trials):
    meta = f"""
    <a name="metadata"></a>
    <h1>Report Metadata & Version</h1>
    <ul style="font-size:9pt;">
        <li><b>Report Generated By:</b> {escape_html(agent_id)}</li>
        <li><b>Report Version:</b> {escape_html(version)}</li>
        <li><b>Created At:</b> {escape_html(dt_str)}</li>
        <li><b>Workflow ID:</b> {escape_html(workflow_id)}</li>
        <li><b>PDF File Path (server):</b> {escape_html(pdf_path)}</li>
        <li><b>PubMed articles included:</b> {len(pubmed.get("articles", [])) if pubmed else 0}</li>
        <li><b>Clinical trials included:</b> {len(trials.get("trials_data", [])) if trials else 0}</li>
    </ul>
    """
    return meta


class ReportBuilderAgentLogic:
    def __init__(
        self,
        agent_id: str,
        version: str,
        logger_instance: Optional[logging.Logger] = None,
    ):
        self.agent_id = agent_id
        self.version = version
        self.logger = logger_instance if logger_instance else logger_rb_logic_default
        self.logger.info(
            f"ReportBuilderAgentLogic initialized. Agent ID: {self.agent_id}, Version: {self.version}."
        )
        self.logger.info(f"Reports directory ready: {REPORTS_OUTPUT_DIR}")
        self.logger.info(f"Templates directory: {TEMPLATES_DIR}")

        # Initialize Jinja2 environment with the correct templates directory
        try:
            self.jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
            self.logger.info(
                f"Jinja2 environment initialized with templates from: {TEMPLATES_DIR}"
            )

            # Check if pa_summary_template.html exists
            template_file = TEMPLATES_DIR / "pa_summary_template.html"
            if template_file.exists():
                self.logger.info(f"Found PA summary template at: {template_file}")
            else:
                self.logger.warning(
                    f"PA summary template not found at: {template_file}"
                )

        except Exception as e:
            self.logger.error(
                f"Failed to initialize Jinja2 environment: {e}", exc_info=True
            )
            raise

    def get_capabilities(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "build_final_report",
                "description": "Compiles research information into a highly professional PDF evidence report.",
                "parameters": {
                    "original_goal": "string (research objective)",
                    "pubmed_articles": "resolved from step dependencies",
                    "clinical_trials": "resolved from step dependencies",
                    "drug_safety": "resolved from step dependencies",
                    "workflow_id": "string (optional, for report metadata)",
                    "report_type": "string (type of report to generate)",
                    "report_data": "dict (data for specific report types)",
                },
                "output_formats": ["pdf"],
                "features": [
                    "executive_summary",
                    "background",
                    "methods",
                    "clickable_toc",
                    "figures",
                    "professional_formatting",
                    "title_page_logo",
                    "numbered_sections",
                    "data_tables",
                    "footer",
                    "page_numbers",
                    "references",
                    "error_handling",
                    "prior_authorization_summary",
                ],
            }
        ]

    def _convert_html_to_pdf(self, html_content: str, pdf_filepath: str) -> bool:
        try:
            # Renderer selection via env with graceful fallback
            preferred_renderer = (os.getenv("HTML_RENDERER") or "").strip().lower()

            # 1) WeasyPrint (if requested or xhtml2pdf unavailable)
            if (preferred_renderer == "weasyprint" and WEASYPRINT_AVAILABLE) or (
                not XHTML2PDF_AVAILABLE and WEASYPRINT_AVAILABLE
            ):
                try:
                    WEASY_HTML(string=html_content).write_pdf(pdf_filepath)
                except Exception as we_err:
                    self.logger.error(f"WeasyPrint render failed: {we_err}")
                    # Fall through to other renderers
                else:
                    # validate below
                    pass

            # 2) xhtml2pdf (default path)
            if (
                XHTML2PDF_AVAILABLE
                and pisa is not None
                and not os.path.exists(pdf_filepath)
            ):
                with open(pdf_filepath, "wb") as pdf_file_handle:
                    pdf_context = pisa.CreatePDF(
                        html_content, dest=pdf_file_handle, encoding="utf-8"
                    )
                    if pdf_context.err:
                        self.logger.error(f"pisa.CreatePDF error: {pdf_context.err}")
                        # Remove incomplete file if any
                        try:
                            if os.path.exists(pdf_filepath):
                                os.remove(pdf_filepath)
                        except Exception:
                            pass

            # 3) Fallback: generate a valid PDF using ReportLab (no HTML rendering)
            if not os.path.exists(pdf_filepath):
                try:
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.pagesizes import A4
                except Exception as imp_err:
                    self.logger.error(
                        f"PDF fallback unavailable (reportlab import failed): {imp_err}"
                    )
                    return False
                tmp_path = pdf_filepath + ".tmp"
                c = canvas.Canvas(tmp_path, pagesize=A4)
                c.setTitle("BabyShield Report")
                c.drawString(72, 800, "BabyShield Report")
                c.drawString(
                    72,
                    784,
                    "Note: HTML renderer not available; using PDF fallback content.",
                )
                c.showPage()
                c.save()
                try:
                    os.replace(tmp_path, pdf_filepath)
                except Exception:
                    # Best-effort move
                    import shutil

                    shutil.copyfile(tmp_path, pdf_filepath)
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

            # Validate header is %PDF
            if os.path.exists(pdf_filepath) and os.path.getsize(pdf_filepath) > 4:
                with open(pdf_filepath, "rb") as fh:
                    sig = fh.read(4)
                if sig == b"%PDF":
                    return True
                self.logger.error(
                    "Generated file is not a valid PDF (missing %PDF header)"
                )
                return False
            else:
                self.logger.error("PDF file created but empty or missing.")
                return False
        except Exception as e:
            self.logger.error(f"Exception during HTML-to-PDF: {e}", exc_info=True)
            return False

    def generate_pdf_from_template(self, template_name: str, context: dict) -> str:
        """Generate PDF from Jinja2 template"""
        try:
            # Check if template exists
            template_path = TEMPLATES_DIR / template_name
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_path}")

            self.logger.info(f"Loading template: {template_name}")
            template = self.jinja_env.get_template(template_name)

            self.logger.info(
                f"Rendering template with context keys: {list(context.keys())}"
            )
            html_content = template.render(**context)

            # Generate PDF filename
            pdf_filename = f"PA_Summary_{str(uuid.uuid4())[:8]}.pdf"
            pdf_filepath = os.path.join(REPORTS_OUTPUT_DIR, pdf_filename)

            self.logger.info(f"Converting HTML to PDF: {pdf_filepath}")
            # Convert to PDF
            if self._convert_html_to_pdf(html_content, pdf_filepath):
                self.logger.info(f"PDF successfully generated: {pdf_filepath}")
                return pdf_filepath
            else:
                raise Exception("PDF conversion failed")

        except Exception as e:
            self.logger.error(
                f"Failed to generate PDF from template: {e}", exc_info=True
            )
            raise

    def _build_pa_summary_report(self, data: dict, workflow_id: str = None) -> dict:
        """Build Prior Authorization Summary Report"""
        self.logger.info("Building Prior Authorization Summary PDF...")
        self.logger.info(f"Received data keys: {list(data.keys())}")

        # Template name
        template_name = "pa_summary_template.html"

        # Prepare context for the template
        context = {
            "prediction_data": data,
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
            "workflow_id": workflow_id or f"WF_{str(uuid.uuid4())[:8]}",
            "logo_path": f"file:///{LOGO_PATH.replace(chr(92), '/')}",
        }

        try:
            # Generate PDF using the template
            pdf_path = self.generate_pdf_from_template(template_name, context)

            self.logger.info(f"Successfully generated PA Summary report at: {pdf_path}")
            return {
                "status": "success",
                "pdf_path": pdf_path,
                "report_type": "prior_authorization_summary",
                "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except FileNotFoundError as e:
            error_msg = f"Template file not found: {e}. Please ensure pa_summary_template.html exists in {TEMPLATES_DIR}"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        except Exception as e:
            self.logger.error(f"Failed to build PA summary report: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def _compute_composite_risk(
        self, recalls: List[dict], community: dict, hazards: dict
    ) -> Dict[str, Any]:
        """Compute a simple deterministic composite risk score and level."""
        score = 0
        level = "LOW"
        # recalls weight
        if recalls:
            # weight by count and severity proxy
            score += min(80, 40 + len(recalls) * 10)
        # community incidents weight
        incidents = int(community.get("incident_count", 0)) if community else 0
        score += min(15, incidents * 2)
        # hazards high flags
        high_flags = 0
        if hazards and isinstance(hazards.get("hazards_identified"), list):
            for h in hazards["hazards_identified"]:
                if (h.get("severity") or "").upper() in ("HIGH", "CRITICAL"):
                    high_flags += 1
        score += min(20, high_flags * 5)
        score = max(0, min(100, score))
        if score >= 85:
            level = "CRITICAL"
        elif score >= 70:
            level = "HIGH"
        elif score >= 40:
            level = "MEDIUM"
        else:
            level = "LOW"
        return {"score": score, "level": level}

    def _build_product_safety_report(
        self, data: dict, workflow_id: Optional[str] = None
    ) -> dict:
        """
        Build BabyShield Product Safety Report (Level 1). Expects a pre-aggregated 'data' dict
        with keys: product, recalls, personalized, community, manufacturer, hazards.
        This method renders the product_safety_report.html template to PDF.
        """
        try:
            template_name = "product_safety_report.html"
            # Validate template exists
            if not (TEMPLATES_DIR / template_name).exists():
                return {
                    "status": "error",
                    "message": f"Template not found: {TEMPLATES_DIR / template_name}",
                }

            # Coerce expected fields with defaults
            product = data.get("product", {}) or {}
            recalls = data.get("recalls", []) or []
            personalized = data.get("personalized", {}) or {}
            community = data.get("community", {}) or {}
            manufacturer = data.get("manufacturer", {}) or {}
            hazards = data.get("hazards", {}) or {}

            # Compute composite risk
            risk = self._compute_composite_risk(
                recalls=recalls, community=community, hazards=hazards
            )

            # Final assessment text (deterministic)
            final_assessment = {
                "CRITICAL": "CRITICAL RISK - Immediate action recommended",
                "HIGH": "HIGH RISK - Action recommended",
                "MEDIUM": "MEDIUM RISK - Use caution and monitor",
                "LOW": "LOW RISK - No issues detected at this time",
            }[risk["level"]]

            # Executive summary
            if recalls:
                hazard_summary = (recalls[0].get("hazard") or "safety issue").strip()
                exec_summary = f"Active recall(s) detected. Primary issue: {hazard_summary}. Discontinue use until resolved."
            else:
                exec_summary = "No official recalls detected. No community spikes observed. Continue normal use with standard safety precautions."

            # Generate QR (optional) - Link to live web version of report
            basename = f"product_{uuid.uuid4().hex[:8]}"
            report_id = workflow_id or uuid.uuid4().hex[:8]
            # QR code links to live web version for easy sharing with partners/pediatricians
            live_report_url = f"{COMPANY_URL}/reports/view/{report_id}"
            qr_path = (
                generate_qr_code(live_report_url, REPORTS_OUTPUT_DIR, basename)
                if QRCODE_AVAILABLE
                else None
            )

            # Determine which data sources were checked
            data_sources_checked = []
            if recalls:
                # Extract unique agencies from recalls
                agencies_in_recalls = set()
                for r in recalls:
                    agency = r.get("agency") or r.get("source_agency") or ""
                    if agency:
                        agencies_in_recalls.add(agency)
                data_sources_checked = list(agencies_in_recalls)

            # If no recalls, show default agencies we check
            if not data_sources_checked:
                data_sources_checked = [
                    "CPSC",
                    "FDA",
                    "EU Safety Gate",
                    "Health Canada",
                    "ACCC (Australia)",
                ]

            # Conditional section visibility based on risk level
            show_recall_details = len(recalls) > 0
            show_critical_warning = risk["level"] in ["CRITICAL", "HIGH"]

            # Build context
            context = {
                "company_name": COMPANY_NAME,
                "report_date": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M UTC"
                ),
                "workflow_id": workflow_id or f"WF_{uuid.uuid4().hex[:8]}",
                "logo_path": f"file:///{LOGO_PATH.replace(chr(92), '/')}"
                if LOGO_PATH
                else None,
                "data_sources_checked": data_sources_checked,
                "show_recall_details": show_recall_details,
                "show_critical_warning": show_critical_warning,
                "product": {
                    "product_name": product.get("product_name"),
                    "brand": product.get("brand"),
                    "upc_gtin": product.get("upc_gtin")
                    or product.get("upc")
                    or product.get("gtin"),
                    "model_number": product.get("model_number"),
                    "lot_or_serial": product.get("lot_or_serial")
                    or product.get("lot_number")
                    or product.get("serial_number"),
                },
                "risk": {
                    "score": risk["score"],
                    "level": risk["level"],
                    "final_assessment": final_assessment,
                    "summary": exec_summary,
                },
                "recalls": [
                    {
                        "id": r.get("id") or r.get("recall_id"),
                        "agency": r.get("agency") or r.get("source_agency"),
                        "date": r.get("date") or (r.get("recall_date") or ""),
                        "hazard": r.get("hazard"),
                        "remedy": r.get("remedy"),
                        "match_confidence": float(r.get("match_confidence", 1.0)),
                        "match_type": r.get("match_type", "exact"),
                    }
                    for r in recalls
                ],
                "personalized": {
                    "pregnancy_status": personalized.get("pregnancy_status"),
                    "allergy_status": personalized.get("allergy_status"),
                    "notes": personalized.get("notes"),
                },
                "community": {
                    "incident_count": community.get("incident_count"),
                    "sentiment": community.get("sentiment"),
                    "summary": community.get("summary"),
                },
                "manufacturer": {
                    "name": manufacturer.get("name"),
                    "compliance_score": manufacturer.get("compliance_score"),
                    "recall_history": manufacturer.get("recall_history"),
                },
                "disclaimers": [
                    "This report is for informational purposes only and does not guarantee safety.",
                    "Always verify with official agency notices and manufacturer guidance.",
                    "Discontinue use if a recall is active or a serious hazard is suspected.",
                    "Keep products within age-appropriate guidelines and follow instructions.",
                    "Personalized checks (allergy/pregnancy) are best-effort and not exhaustive.",
                    "This is not medical or legal advice.",
                    "Use at your own discretion; BabyShield is not liable for misuse.",
                ],
                "qr_path": ("file:///" + qr_path.replace("\\", "/"))
                if qr_path
                else None,
            }

            # Render
            template = self.jinja_env.get_template(template_name)
            html_content = template.render(**context)

            # Output PDF
            pdf_filename = f"Product_Safety_Report_{uuid.uuid4().hex[:8]}.pdf"
            pdf_filepath = os.path.join(REPORTS_OUTPUT_DIR, pdf_filename)

            if not self._convert_html_to_pdf(html_content, pdf_filepath):
                return {"status": "error", "message": "PDF conversion failed"}

            return {
                "status": "success",
                "pdf_path": pdf_filepath,
                "report_type": "product_safety",
                "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error(
                f"Failed to build product safety report: {e}", exc_info=True
            )
            return {"status": "error", "message": str(e)}

    def _build_nursery_quarterly_report(
        self, data: dict, workflow_id: Optional[str] = None
    ) -> dict:
        """
        Build Nursery Quarterly Report over multiple products.
        Expects data: { products: [ {product, recalls, personalized, community, manufacturer, hazards}, ... ] }
        """
        try:
            template_name = "nursery_quarterly_report.html"
            if not (TEMPLATES_DIR / template_name).exists():
                return {
                    "status": "error",
                    "message": f"Template not found: {TEMPLATES_DIR / template_name}",
                }

            items = data.get("products", []) or []
            rendered_items = []
            high_risk = 0
            new_recalls = 0
            nearing_expiry = 0

            for entry in items:
                product = entry.get("product", {}) or {}
                recalls = entry.get("recalls", []) or []
                community = entry.get("community", {}) or {}
                hazards = entry.get("hazards", {}) or {}
                risk = self._compute_composite_risk(recalls, community, hazards)
                if risk["level"] in ("HIGH", "CRITICAL"):
                    high_risk += 1
                final_assessment = {
                    "CRITICAL": "CRITICAL RISK - Immediate action recommended",
                    "HIGH": "HIGH RISK - Action recommended",
                    "MEDIUM": "MEDIUM RISK - Use caution and monitor",
                    "LOW": "LOW RISK - No issues detected at this time",
                }[risk["level"]]
                if recalls:
                    hazard_summary = (
                        recalls[0].get("hazard") or "safety issue"
                    ).strip()
                    summary = (
                        f"Active recall(s) detected. Primary issue: {hazard_summary}."
                    )
                else:
                    summary = "No official recalls detected in the period."
                rendered_items.append(
                    {
                        "product": {
                            "product_name": product.get("product_name"),
                            "brand": product.get("brand"),
                            "upc_gtin": product.get("upc_gtin")
                            or product.get("upc")
                            or product.get("gtin"),
                            "model_number": product.get("model_number"),
                            "lot_or_serial": product.get("lot_or_serial")
                            or product.get("lot_number")
                            or product.get("serial_number"),
                        },
                        "recalls": [
                            {
                                "id": r.get("id") or r.get("recall_id"),
                                "agency": r.get("agency") or r.get("source_agency"),
                                "date": r.get("date") or (r.get("recall_date") or ""),
                                "hazard": r.get("hazard"),
                                "remedy": r.get("remedy"),
                            }
                            for r in recalls
                        ],
                        "risk": {
                            "score": risk["score"],
                            "level": risk["level"],
                            "final_assessment": final_assessment,
                            "summary": summary,
                        },
                    }
                )

            # Collect all unique data sources from all products
            all_agencies = set()
            for item in items:
                recalls = item.get("recalls", []) or []
                for r in recalls:
                    agency = r.get("agency") or r.get("source_agency") or ""
                    if agency:
                        all_agencies.add(agency)

            data_sources_checked = (
                list(all_agencies)
                if all_agencies
                else [
                    "CPSC",
                    "FDA",
                    "EU Safety Gate",
                    "Health Canada",
                    "ACCC (Australia)",
                ]
            )

            context = {
                "company_name": COMPANY_NAME,
                "report_date": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M UTC"
                ),
                "workflow_id": workflow_id or f"WF_{uuid.uuid4().hex[:8]}",
                "logo_path": f"file:///{LOGO_PATH.replace(chr(92), '/')}"
                if LOGO_PATH
                else None,
                "data_sources_checked": data_sources_checked,
                "summary": {
                    "total_products": len(rendered_items),
                    "high_risk_count": high_risk,
                    "new_recalls_count": new_recalls,
                    "nearing_expiry_count": nearing_expiry,
                },
                "products": rendered_items,
                "disclaimers": [
                    "This report is for informational purposes only and does not guarantee safety.",
                    "Always verify with official agency notices and manufacturer guidance.",
                    "Discontinue use if a recall is active or a serious hazard is suspected.",
                    "Keep products within age-appropriate guidelines and follow instructions.",
                    "Personalized checks (allergy/pregnancy) are best-effort and not exhaustive.",
                    "This is not medical or legal advice.",
                    "Use at your own discretion; BabyShield is not liable for misuse.",
                ],
            }
            template = self.jinja_env.get_template(template_name)
            html_content = template.render(**context)
            pdf_filename = f"Nursery_Quarterly_Report_{uuid.uuid4().hex[:8]}.pdf"
            pdf_filepath = os.path.join(REPORTS_OUTPUT_DIR, pdf_filename)
            if not self._convert_html_to_pdf(html_content, pdf_filepath):
                return {"status": "error", "message": "PDF conversion failed"}
            return {
                "status": "success",
                "pdf_path": pdf_filepath,
                "report_type": "nursery_quarterly",
                "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error(
                f"Failed to build nursery quarterly report: {e}", exc_info=True
            )
            return {"status": "error", "message": str(e)}

    def _build_default_research_report(self, data: dict) -> dict:
        """Keep the existing logic for building the old research reports"""
        self.logger.info("Building default research report...")
        return {"status": "success", "message": "Default research report built"}

    def _render_pdf(self, html_content: str, filename_prefix: str) -> dict:
        pdf_filename = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.pdf"
        pdf_filepath = os.path.join(REPORTS_OUTPUT_DIR, pdf_filename)
        if not self._convert_html_to_pdf(html_content, pdf_filepath):
            return {"status": "error", "message": "PDF conversion failed"}
        return {
            "status": "success",
            "pdf_path": pdf_filepath,
            "report_type": filename_prefix,
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def build_safety_summary(self, db, user_id: int, window_days: int = 90) -> dict:
        """Generate a simple safety summary report over recent recalls."""
        try:
            from core_infra.database import RecallDB as RecallModel
        except Exception:
            RecallModel = None

        recalls = []
        if RecallModel and db is not None:
            try:
                recalls = (
                    db.query(RecallModel)
                    .order_by(RecallModel.recall_date.desc())
                    .limit(15)
                    .all()
                )
            except Exception as e:
                self.logger.error(f"Failed to fetch recalls for summary: {e}")
                recalls = []

        hazards = [
            (getattr(r, "hazard_category", None) or getattr(r, "hazard", None))
            for r in recalls
            if r
        ]
        brands = [getattr(r, "brand", None) for r in recalls if r]

        def top(xs, k):
            return [v for v, _ in Counter([x for x in xs if x]).most_common(k)]

        ctx = {
            "title": "Nursery Safety Summary",
            "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
            "window_days": window_days,
            "stats": {
                "total_recalls": len(recalls),
                "top_hazards": top(hazards, 3),
                "top_brands": top(brands, 4),
            },
            "recalls": recalls,
            "header_logo": "",
        }

        try:
            template = self.jinja_env.get_template("safety_summary_template.html")
            html = template.render(**ctx)
            return self._render_pdf(html, filename_prefix="safety_summary")
        except Exception as e:
            self.logger.error(f"Safety summary build failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def build_report(self, task_payload: dict) -> dict:
        """Main method to build reports based on type"""
        report_type = task_payload.get("report_type", "default_research")
        report_data = task_payload.get("report_data", {})
        workflow_id = task_payload.get("workflow_id")

        self.logger.info(f"Building report of type: {report_type}")

        if report_type == "prior_authorization_summary":
            # Call the dedicated method for PA reports
            return self._build_pa_summary_report(report_data, workflow_id)
        elif report_type == "product_safety":
            return self._build_product_safety_report(report_data, workflow_id)
        elif report_type == "nursery_quarterly":
            return self._build_nursery_quarterly_report(report_data, workflow_id)
        elif report_type == "safety_summary":
            db = report_data.get("db") if isinstance(report_data, dict) else None
            user_id = (
                report_data.get("user_id") if isinstance(report_data, dict) else None
            )
            return self.build_safety_summary(db, user_id=user_id or 0)
        else:
            # Keep the existing logic for building the old research reports
            return self._build_default_research_report(report_data)

    def _extract_data_from_dependency_result(
        self, dep_result: Any, expected_key: str
    ) -> Dict[str, Any]:
        """
        Enhanced extraction logic that handles various formats of dependency results.
        This is more flexible and can handle nested structures.
        """
        if not dep_result:
            self.logger.warning(f"No dependency result for {expected_key}")
            return {}

        # If it's already a dict, check various possible structures
        if isinstance(dep_result, dict):
            # Direct format (the data we want is at the top level)
            if (
                "articles" in dep_result
                or "trials_data" in dep_result
                or "top_adverse_reactions" in dep_result
            ):
                return dep_result

            # Nested in 'result' key
            if "result" in dep_result and isinstance(dep_result["result"], dict):
                return dep_result["result"]

            # Nested in 'data' key
            if "data" in dep_result and isinstance(dep_result["data"], dict):
                return dep_result["data"]

            # Check for expected_key as a nested key
            if expected_key in dep_result and isinstance(
                dep_result[expected_key], dict
            ):
                return dep_result[expected_key]

            # If we have status=success, try to find the actual data
            if (
                dep_result.get("status") == "success"
                or dep_result.get("status") == "COMPLETED"
            ):
                # Look for common data keys
                for key in ["result", "data", "output", "response"]:
                    if key in dep_result and isinstance(dep_result[key], dict):
                        return dep_result[key]

            # Last resort - return as is
            return dep_result

        # If it's not a dict, log warning and return empty
        self.logger.warning(
            f"Dependency result for {expected_key} is not a dict: {type(dep_result)}"
        )
        return {}

    def _compose_html_report(
        self,
        context: Dict[str, Any],
        logo_path: str,
        chart_path: Optional[str],
        qr_path: Optional[str],
        pdf_path: str,
    ) -> str:
        pubmed = context.get("pubmed_articles", {})
        trials = context.get("clinical_trials_info", {})
        safety = context.get("drug_safety_info", {})
        goal = context.get("original_goal", "")

        # Enhanced extraction of drug and disease info
        drug = None
        disease = None

        # Try to get from pubmed data
        if pubmed:
            drug = pubmed.get("drug_queried") or pubmed.get("drug_name")
            disease = pubmed.get("disease_queried") or pubmed.get("disease_name")

        # If not found, try to extract from original goal or other sources
        if not drug and context.get("extracted_drug_name"):
            drug = context["extracted_drug_name"]
        if not disease and context.get("extracted_disease_name"):
            disease = context["extracted_disease_name"]

        workflow_id = context.get("workflow_id", "")
        dt_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        toc = """
        <div style="page-break-after:always;">
            <h2>Table of Contents</h2>
            <ul style="font-size:13pt; line-height:1.8;">
                <li><a href="#executive_summary">Executive Summary</a></li>
                <li><a href="#background">Background & Context</a></li>
                <li><a href="#methods">Methods</a></li>
                <li><a href="#literature">Literature Review</a></li>
                <li><a href="#trials">Clinical Trials</a></li>
                <li><a href="#adverse_events">Drug Safety Profile</a></li>
                <li><a href="#references">References</a></li>
                <li><a href="#disclaimer">Disclaimer & Contact</a></li>
                <li><a href="#metadata">Report Metadata & Version</a></li>
            </ul>
        </div>
        """

        html = f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<style>
@page {{
    size: A4 portrait;
    margin: 0.8in;
    @frame footer_frame {{
      -pdf-frame-content: footer_content;
      left: 0.8in; width: 6.7in; bottom: 0.4in; height: 0.5in;
    }}
}}
body {{ font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 10pt; color: #242729; }}
h1 {{ color: #1a237e; font-size: 18pt; border-bottom: 1px solid #2980b9; margin-top: 1.6em; margin-bottom: 0.8em; }}
h2 {{ color: #2980b9; font-size: 14pt; margin-top: 1.4em; margin-bottom: 0.6em; }}
th {{ background-color: #e8f0fe; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; }}
th, td {{ border: 1px solid #d0d6db; padding: 7px; text-align: left; word-break: break-word; }}
a {{ color: #2561b1; text-decoration: none; }}
.disclaimer {{ font-size: 8.5pt; color: #707070; margin-top: 2em; border-top: 1px solid #cccccc; padding-top: 1em; text-align: center;}}
.toc-list li {{ margin-bottom: 7px; }}
</style>
</head>
<body>
<div style="text-align:center; margin-top:40px; margin-bottom:10px;">
    {html_img_tag(logo_path, width=170, style="margin-bottom:12px;")}
    <h1 style="margin-bottom:8px;">{COMPANY_NAME} Evidence Report</h1>
    <div style="font-size:15pt; color:#223962; margin-bottom:7px;">{TAGLINE}</div>
    <div style="font-size:10.5pt; margin-bottom:18px;">Generated by: {self.agent_id} (v{self.version})</div>
    <div style="font-size:10pt; margin-bottom:5px;">
        <b>Date:</b> {dt_str}
        &nbsp; | &nbsp; <b>Workflow ID:</b> {escape_html(workflow_id)}
    </div>
    <div style="font-size:9.5pt; color:#657384;">
        <a href="{COMPANY_URL}">{COMPANY_URL}</a>
        &nbsp;|&nbsp; Contact: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>
    </div>
</div>
<hr style="margin-top:10px; margin-bottom:20px; border: none; border-top: 2px solid #2980b9;">
{toc}

{format_highlights(pubmed, trials, safety)}
{format_executive_summary(pubmed, trials, safety)}
{format_background(goal, drug, disease)}
{format_methods()}
{format_pubmed_articles(pubmed)}
{format_clinical_trials(trials)}
{format_adverse_events(safety, chart_path)}
{format_references(pubmed, trials)}
{format_disclaimer()}
{format_metadata(self.agent_id, self.version, dt_str, workflow_id, pdf_path, pubmed, trials)}
"""

        # QR code block
        if qr_path and os.path.exists(qr_path):
            qr_path_url = "file:///" + qr_path.replace("\\", "/")
            html += f'<div style="text-align:center;margin-top:18px;"><img src="{qr_path_url}" width="120" alt="QR Code"></div>'

        html += """
<div id="footer_content" style="text-align:center; font-size:9pt; color:#808080;">
    Page <pdf:pagenumber /> of <pdf:pagecount /> &nbsp;|&nbsp; Workflow ID: {workflow_id} &nbsp;|&nbsp; CureViaX Confidential
</div>
</body></html>
""".format(
            workflow_id=escape_html(workflow_id)
        )
        return html

    async def process_message(
        self, message_data: Dict[str, Any], client: Any
    ) -> Optional[Dict[str, Any]]:
        header = message_data.get("mcp_header", {})
        payload = message_data.get("payload", {})
        message_type_str = header.get("message_type", "UNKNOWN")
        sender_id = header.get("sender_id", "UnknownSender")
        correlation_id = header.get("correlation_id")
        task_id = payload.get("task_id", "task_id_missing_in_assign_payload")

        try:
            message_type = MessageType(message_type_str)
        except ValueError:
            self.logger.warning(
                f"Unknown msg type '{message_type_str}' from {sender_id}. Ignoring."
            )
            return None

        if message_type == MessageType.PONG:
            return None
        if message_type == MessageType.DISCOVERY_ACK:
            return None

        if message_type == MessageType.TASK_ASSIGN:
            self.logger.info(
                f"Processing TASK_ASSIGN from {sender_id} for task {task_id}"
            )

            task_parameters = payload.get("parameters", {})
            workflow_id = (
                payload.get("workflow_id")
                or correlation_id
                or f"WF_{str(uuid.uuid4())[:8]}"
            )

            # Check if this is a prior authorization report request
            report_type = task_parameters.get("report_type", "default_research")

            if report_type == "prior_authorization_summary":
                # Handle the new PA summary report
                report_data = task_parameters.get("report_data", {})

                # If report_data is a string (from template substitution), try to parse it
                if isinstance(report_data, str):
                    try:
                        import json

                        report_data = json.loads(report_data)
                        self.logger.info("Successfully parsed report_data from string")
                    except json.JSONDecodeError:
                        self.logger.error(
                            f"Failed to parse report_data as JSON: {report_data[:100]}..."
                        )
                        report_data = {"error": "Failed to parse prediction data"}

                # Check dependency results for actual data from step6
                dependency_results = task_parameters.get("dependency_results", {})
                if dependency_results:
                    # Look for the result from step6_predict_approval_likelihood
                    for key in [
                        "step6_predict_approval_likelihood",
                        "step7_generate_report",
                    ]:
                        if key in dependency_results:
                            dep_result = dependency_results[key]
                            if isinstance(dep_result, dict):
                                if "result" in dep_result:
                                    report_data = dep_result["result"]
                                elif "prediction" in dep_result:
                                    report_data = dep_result["prediction"]
                                break

                result = await self.build_report(
                    {
                        "report_type": report_type,
                        "report_data": report_data,
                        "workflow_id": workflow_id,
                    }
                )

                response_payload = {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "status": "COMPLETED"
                    if result.get("status") == "success"
                    else "FAILED",
                    "result": result,
                    "error_message": result.get("message")
                    if result.get("status") != "success"
                    else None,
                }

                return {
                    "message_type": MessageType.TASK_COMPLETE.value
                    if result.get("status") == "success"
                    else MessageType.TASK_FAIL.value,
                    "payload": response_payload,
                }

            # Otherwise, handle the existing research report logic
            dependency_results = task_parameters.get("dependency_results", {})
            if not isinstance(dependency_results, dict):
                self.logger.warning("dependency_results not dict. Using empty.")
                dependency_results = {}

            # Log the structure we received for debugging
            self.logger.debug(
                f"Received dependency_results keys: {list(dependency_results.keys())}"
            )
            for key, value in dependency_results.items():
                if isinstance(value, dict):
                    self.logger.debug(
                        f"  {key} has keys: {list(value.keys())[:5]}..."
                    )  # First 5 keys

            # Extract parameters with fallbacks
            original_goal = (
                task_parameters.get("original_goal")
                or task_parameters.get("goal")
                or payload.get("original_goal")
                or "Research Topic Not Specified"
            )

            workflow_id_for_report = workflow_id

            # Enhanced extraction with multiple fallback strategies
            # Try to get pubmed data
            pubmed_articles_data = None
            for key in [
                "step1_pubmed_search",
                "pubmed_articles",
                "pubmed",
                "literature",
            ]:
                if key in dependency_results:
                    pubmed_articles_data = self._extract_data_from_dependency_result(
                        dependency_results[key], "pubmed"
                    )
                    if pubmed_articles_data:
                        self.logger.info(f"Found pubmed data under key: {key}")
                        break

            # Try to get clinical trials data
            clinical_trials_data = None
            for key in [
                "step2a_find_trials",
                "clinical_trials",
                "trials",
                "clinical_trials_info",
            ]:
                if key in dependency_results:
                    clinical_trials_data = self._extract_data_from_dependency_result(
                        dependency_results[key], "trials"
                    )
                    if clinical_trials_data:
                        self.logger.info(f"Found trials data under key: {key}")
                        break

            # Try to get drug safety data
            drug_safety_data_from_deps = None
            for key in [
                "step2b_check_drug_safety",
                "drug_safety",
                "safety_data",
                "adverse_events",
            ]:
                if key in dependency_results:
                    drug_safety_data_from_deps = (
                        self._extract_data_from_dependency_result(
                            dependency_results[key], "safety"
                        )
                    )
                    if drug_safety_data_from_deps:
                        self.logger.info(f"Found safety data under key: {key}")
                        break

            # If we still don't have data, check if parameters have direct references
            if not pubmed_articles_data and "pubmed_articles" in task_parameters:
                pubmed_articles_data = task_parameters["pubmed_articles"]
            if not clinical_trials_data and "clinical_trials" in task_parameters:
                clinical_trials_data = task_parameters["clinical_trials"]
            if not drug_safety_data_from_deps and "safety_data" in task_parameters:
                drug_safety_data_from_deps = task_parameters["safety_data"]

            # Log what we found
            self.logger.info("Data extraction results:")
            self.logger.info(
                f"  - PubMed articles: {'Found' if pubmed_articles_data else 'Not found'}"
            )
            self.logger.info(
                f"  - Clinical trials: {'Found' if clinical_trials_data else 'Not found'}"
            )
            self.logger.info(
                f"  - Drug safety: {'Found' if drug_safety_data_from_deps else 'Not found'}"
            )

            # Generate chart if we have safety data
            chart_path = None
            if drug_safety_data_from_deps:
                top_reactions = drug_safety_data_from_deps.get(
                    "top_adverse_reactions", []
                )
                if top_reactions:
                    chart_path = generate_adverse_event_chart(
                        top_reactions,
                        REPORTS_OUTPUT_DIR,
                        f"chart_{task_id}_{uuid.uuid4().hex[:6]}",
                    )

            # Generate filename
            safe_goal_filename_part = (
                "".join(
                    c if c.isalnum() or c in (" ") else "_" for c in original_goal[:50]
                )
                .replace(" ", "_")
                .rstrip("_")
            )
            if not safe_goal_filename_part:
                safe_goal_filename_part = "CureViaX_Report"

            pdf_filename = f"{safe_goal_filename_part}_{str(uuid.uuid4())[:8]}.pdf"
            pdf_filepath = os.path.join(REPORTS_OUTPUT_DIR, pdf_filename)

            # Generate QR code
            qr_data = f"{COMPANY_URL}/view/{pdf_filename}"
            qr_path = generate_qr_code(
                qr_data, REPORTS_OUTPUT_DIR, f"qr_{task_id}_{uuid.uuid4().hex[:6]}"
            )

            # Prepare context with all extracted data
            context = {
                "pubmed_articles": pubmed_articles_data or {},
                "clinical_trials_info": clinical_trials_data or {},
                "drug_safety_info": drug_safety_data_from_deps or {},
                "original_goal": original_goal,
                "workflow_id": workflow_id_for_report,
                "extracted_drug_name": task_parameters.get("extracted_drug_name"),
                "extracted_disease_name": task_parameters.get("extracted_disease_name"),
            }

            # Generate HTML report
            try:
                html = self._compose_html_report(
                    context, LOGO_PATH, chart_path, qr_path, pdf_filepath
                )

                # Convert to PDF
                pdf_creation_success = self._convert_html_to_pdf(html, pdf_filepath)

                if pdf_creation_success:
                    self.logger.info(
                        f"PDF report generated successfully: {pdf_filepath}"
                    )
                    generation_status_msg_part = "succeeded and file created."
                else:
                    self.logger.error(f"PDF generation failed for: {pdf_filepath}")
                    generation_status_msg_part = "failed or file not found."

            except Exception as e:
                self.logger.error(f"Error during report generation: {e}", exc_info=True)
                pdf_creation_success = False
                generation_status_msg_part = f"failed with error: {str(e)}"

            # Prepare response
            result_payload_content = {
                "report_title": original_goal,
                "pdf_file_path": pdf_filepath if pdf_creation_success else None,
                "generation_status_message": f"PDF conversion {generation_status_msg_part}",
                "data_sources": {
                    "pubmed_articles_count": len(
                        pubmed_articles_data.get("articles", [])
                    )
                    if pubmed_articles_data
                    else 0,
                    "clinical_trials_count": len(
                        clinical_trials_data.get("trials_data", [])
                    )
                    if clinical_trials_data
                    else 0,
                    "adverse_events_count": len(
                        drug_safety_data_from_deps.get("top_adverse_reactions", [])
                    )
                    if drug_safety_data_from_deps
                    else 0,
                },
            }

            response_payload = {
                "workflow_id": workflow_id_for_report,
                "task_id": task_id,
                "agent_id": self.agent_id,
                "status": "COMPLETED" if pdf_creation_success else "FAILED",
                "result": result_payload_content,
                "error_message": None
                if pdf_creation_success
                else f"PDF generation {generation_status_msg_part}",
            }

            return {
                "message_type": MessageType.TASK_COMPLETE.value
                if pdf_creation_success
                else MessageType.TASK_FAIL.value,
                "payload": response_payload,
            }
        else:
            self.logger.warning(
                f"ReportBuilderLogic received unhandled message type: {message_type.value}"
            )
            return None

    async def shutdown(self):
        self.logger.info(
            f"ReportBuilderAgentLogic shutting down for agent {self.agent_id}."
        )
        self.logger.info(
            f"ReportBuilderAgentLogic shutdown complete for agent {self.agent_id}"
        )

    # Add this method for direct task processing (for testing without MCP)
    def process_task(self, task_payload: dict) -> dict:
        """Process task directly without MCP messaging"""
        report_type = task_payload.get("report_type", "prior_authorization_summary")
        report_data = task_payload.get("report_data", {})
        workflow_id = task_payload.get("workflow_id", f"WF_{str(uuid.uuid4())[:8]}")

        self.logger.info(f"Direct task processing for report type: {report_type}")

        if report_type == "prior_authorization_summary":
            return self._build_pa_summary_report(report_data, workflow_id)
        else:
            return {
                "status": "error",
                "message": f"Unsupported report type: {report_type}",
            }
