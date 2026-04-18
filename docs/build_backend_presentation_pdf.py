from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parent
markdown_path = ROOT / "BACKEND_IMPLEMENTATION_TECH_STACK_PRESENTATION.md"
pdf_path = ROOT / "BACKEND_IMPLEMENTATION_TECH_STACK_PRESENTATION.pdf"

text = markdown_path.read_text(encoding="utf-8")
lines = text.splitlines()

styles = getSampleStyleSheet()
heading = ParagraphStyle(
    "Heading",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=22,
    spaceAfter=10,
)
section = ParagraphStyle(
    "Section",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=12,
    leading=16,
    spaceBefore=7,
    spaceAfter=4,
)
body = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=14,
    spaceAfter=3,
)

story = []

for line in lines:
    clean = line.rstrip()

    if not clean.strip():
        story.append(Spacer(1, 5))
        continue

    escaped = (
        clean.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    if clean.startswith("# "):
        story.append(Paragraph(escaped[2:], heading))
    elif clean.startswith("## "):
        story.append(Paragraph(escaped[3:], section))
    elif clean.startswith("  - "):
        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;• {escaped[4:]}", body))
    elif clean.startswith("- "):
        story.append(Paragraph(f"• {escaped[2:]}", body))
    else:
        story.append(Paragraph(escaped, body))

pdf = SimpleDocTemplate(
    str(pdf_path),
    pagesize=A4,
    leftMargin=42,
    rightMargin=42,
    topMargin=40,
    bottomMargin=36,
    title="ARIA Backend Implementation and Tech Stack",
)
pdf.build(story)

print(f"PDF created: {pdf_path}")
