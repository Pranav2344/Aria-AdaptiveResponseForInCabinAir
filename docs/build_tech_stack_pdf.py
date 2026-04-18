from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parent
markdown_path = ROOT / "TECH_STACK.md"
pdf_path = ROOT / "TECH_STACK.pdf"

text = markdown_path.read_text(encoding="utf-8")
lines = text.splitlines()

styles = getSampleStyleSheet()
body = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=14,
    spaceAfter=4,
)
heading = ParagraphStyle(
    "Heading",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=16,
    leading=20,
    spaceAfter=10,
)
section = ParagraphStyle(
    "Section",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=12,
    leading=16,
    spaceBefore=6,
    spaceAfter=4,
)

story = []

for line in lines:
    clean = line.strip()

    if not clean:
        story.append(Spacer(1, 6))
        continue

    escaped = (
        clean.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    if clean.startswith("# "):
        story.append(Paragraph(escaped[2:], heading))
        continue

    if clean.startswith("## "):
        story.append(Paragraph(escaped[3:], section))
        continue

    if clean.startswith("- "):
        story.append(Paragraph(f"• {escaped[2:]}", body))
        continue

    if clean.startswith("  - "):
        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;• {escaped[4:]}", body))
        continue

    story.append(Paragraph(escaped, body))

pdf = SimpleDocTemplate(
    str(pdf_path),
    pagesize=A4,
    leftMargin=40,
    rightMargin=40,
    topMargin=40,
    bottomMargin=36,
)
pdf.build(story)

print(f"PDF created: {pdf_path}")
