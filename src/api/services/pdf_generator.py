from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor


def generate_pdf(landmarks, steiner_results, image_path=None, watermark=False):
    """Generate PDF report with landmarks, Steiner table, disclaimer."""
    from io import BytesIO
    buffer = BytesIO()

    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "AI-Cefalo Cephalometric Report")
    c.setFont("Helvetica", 10)
    import datetime
    c.drawString(50, height - 70, f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}")

    # Watermark
    if watermark:
        c.setFont("Helvetica", 50)
        c.setFillColor(HexColor("#E5E7EB", alpha=0.3))
        c.saveState()
        c.translate(width / 2, height / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, "PREVIEW - UNPAID")
        c.restoreState()

    # Steiner Analysis
    y = height - 120
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Steiner Analysis")
    y -= 30

    c.setFont("Helvetica", 10)
    for angle_name, data in steiner_results.items():
        if isinstance(data, dict) and "value" in data:
            text = f"{angle_name}: {data['value']} - {data.get('color', 'N/A')}"
            c.drawString(70, y, text)
            y -= 20

    # Classification
    if "classification" in steiner_results:
        y -= 10
        c.setFont("Helvetica-Bold", 11)
        c.drawString(
            50, y, f"Classification: {steiner_results['classification']['text']}"
        )

    # Disclaimer
    y -= 40
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor("#6B7280"))
    c.drawString(
        50,
        y,
        "Disclaimer: AI-Cefalo es una herramienta educativa de apoyo. "
        "Los resultados no reemplazan el criterio clinico de un profesional certificado.",
    )

    c.save()
    buffer.seek(0)
    return buffer
