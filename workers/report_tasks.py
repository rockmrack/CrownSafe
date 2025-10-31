"""Stub worker task module for report generation

This is a stub implementation for Phase 1 testing.
Real implementation to be added later.
"""

from core_infra.celery_tasks import app


# Mock PDFGenerator for testing
class PDFGenerator:
    """Mock PDF generator service."""

    def __init__(self):
        pass

    def generate(self, data, output_path):
        """Generate PDF from data."""
        return {
            "success": True,
            "page_count": len(data) if isinstance(data, list) else 10,
            "size_mb": 1.2,
        }


@app.task(name="generate_report")
def generate_report_task(report_type, data, user_id):
    """Generate PDF report

    Args:
        report_type: Type of report to generate
        data: Report data
        user_id: User requesting the report

    Returns:
        dict: Report generation result

    """
    # Stub implementation
    pdf_gen = PDFGenerator()
    output_path = f"/tmp/report_{user_id}.pdf"
    result = pdf_gen.generate(data, output_path)

    return {
        "success": True,
        "report_type": report_type,
        "file_path": output_path,
        "size_mb": result["size_mb"],
        "records_processed": len(data) if isinstance(data, list) else 0,
    }


@app.task(name="generate_pdf_report")
def generate_pdf_report_task(data, output_path):
    """Generate PDF from data

    Args:
        data: Data to include in PDF
        output_path: Output file path

    Returns:
        dict: Generation result

    """
    # Stub implementation
    return {
        "success": True,
        "output_path": output_path,
        "page_count": 10,
        "size_mb": 1.2,
    }
