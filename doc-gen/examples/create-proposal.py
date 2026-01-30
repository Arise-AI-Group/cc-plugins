#!/usr/bin/env python3
"""
Professional PDF Proposal Generator

This example demonstrates creating professional PDF documents using reportlab.
Customize the content and styling for your specific proposal needs.

Usage:
    pip install reportlab
    python create-proposal.py [output.pdf]

Output: proposal.pdf (or specified filename)
"""

import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                 PageBreak, KeepTogether)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ===== CONFIGURATION =====
# Customize these values for your proposal

CONFIG = {
    "company": {
        "name": "Your Company",
        "tagline": "Professional Services",
        "email": "contact@yourcompany.com"
    },
    "client": {
        "name": "Client Name",
        "contact": "Contact Person",
        "title": "Client Title",
        "company": "Client Company",
        "address": "123 Client Address, City, State"
    },
    "proposal": {
        "title": "Project Proposal",
        "subtitle": "Service Description",
        "valid_days": 30
    }
}

# ===== COLORS =====
PRIMARY_BLUE = HexColor("#1E3A5F")
ACCENT_BLUE = HexColor("#2E5A8F")
LIGHT_BLUE = HexColor("#E8F0F8")
HEADER_GRAY = HexColor("#4A4A4A")
LIGHT_GREEN = HexColor("#E8F5E9")
LIGHT_ORANGE = HexColor("#FFF3E0")

# ===== STYLES =====
styles = getSampleStyleSheet()

styles.add(ParagraphStyle(name='TitleMain', fontName='Helvetica-Bold', fontSize=20,
                          textColor=PRIMARY_BLUE, alignment=TA_CENTER, spaceAfter=6))
styles.add(ParagraphStyle(name='TitleSub', fontName='Helvetica-Bold', fontSize=16,
                          textColor=ACCENT_BLUE, alignment=TA_CENTER, spaceAfter=4))
styles.add(ParagraphStyle(name='TitleLocation', fontName='Helvetica', fontSize=12,
                          textColor=HEADER_GRAY, alignment=TA_CENTER, spaceAfter=20))
styles.add(ParagraphStyle(name='SectionHeader', fontName='Helvetica-Bold', fontSize=14,
                          textColor=PRIMARY_BLUE, spaceBefore=20, spaceAfter=10))
styles.add(ParagraphStyle(name='SubsectionHeader', fontName='Helvetica-Bold', fontSize=12,
                          textColor=ACCENT_BLUE, spaceBefore=12, spaceAfter=6))
styles.add(ParagraphStyle(name='BodyPara', fontName='Helvetica', fontSize=10,
                          spaceAfter=6, leading=14))
styles.add(ParagraphStyle(name='BulletItem', fontName='Helvetica', fontSize=10,
                          spaceAfter=4, leftIndent=20, leading=14))
styles.add(ParagraphStyle(name='SmallText', fontName='Helvetica', fontSize=9,
                          textColor=HEADER_GRAY))
styles.add(ParagraphStyle(name='CenterText', fontName='Helvetica', fontSize=10,
                          alignment=TA_CENTER))
styles.add(ParagraphStyle(name='ItalicClosing', fontName='Helvetica-Oblique', fontSize=9,
                          textColor=HEADER_GRAY, alignment=TA_CENTER))
styles.add(ParagraphStyle(name='TableHeader', fontName='Helvetica-Bold', fontSize=10,
                          textColor=HexColor("#FFFFFF")))
styles.add(ParagraphStyle(name='TableCell', fontName='Helvetica', fontSize=10))
styles.add(ParagraphStyle(name='WhiteText', fontName='Helvetica', fontSize=10,
                          textColor=HexColor("#FFFFFF"), alignment=TA_CENTER))
styles.add(ParagraphStyle(name='WhiteBold', fontName='Helvetica-Bold', fontSize=11,
                          textColor=HexColor("#FFFFFF"), alignment=TA_CENTER))


def add_header_footer(canvas, doc):
    """Add header and footer to each page."""
    canvas.saveState()

    # Header
    canvas.setFont('Helvetica-Bold', 9)
    canvas.setFillColor(PRIMARY_BLUE)
    canvas.drawRightString(7.5*inch, 10.5*inch, CONFIG["company"]["name"])
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(HEADER_GRAY)
    header_text = f" | {CONFIG['company']['tagline']}"
    canvas.drawRightString(
        7.5*inch + canvas.stringWidth(header_text, 'Helvetica', 9),
        10.5*inch,
        header_text
    )

    # Footer
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(HEADER_GRAY)
    canvas.drawCentredString(
        4.25*inch,
        0.5*inch,
        f"Page {doc.page}  |  {CONFIG['company']['email']}"
    )

    canvas.restoreState()


def create_proposal(output_path: str):
    """Create a professional proposal PDF."""
    from datetime import datetime

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=1*inch, rightMargin=1*inch,
        topMargin=1*inch, bottomMargin=1*inch
    )

    story = []
    date_str = datetime.now().strftime("%B %d, %Y")

    # ===== TITLE SECTION =====
    story.append(Paragraph("PROPOSAL", styles['TitleMain']))
    story.append(Paragraph(CONFIG["proposal"]["subtitle"], styles['TitleSub']))
    story.append(Paragraph(CONFIG["client"]["company"], styles['TitleLocation']))

    # Prepared For / By table
    prep_data = [
        [Paragraph("<b>Prepared for:</b>", styles['SmallText']),
         Paragraph("<b>Prepared by:</b>", styles['SmallText'])],
        [Paragraph(
            f"<b>{CONFIG['client']['contact']}</b><br/>"
            f"{CONFIG['client']['title']}<br/>"
            f"{CONFIG['client']['company']}<br/>"
            f"{CONFIG['client']['address']}",
            styles['BodyPara']),
         Paragraph(
            f"<b>{CONFIG['company']['name']}</b><br/>"
            f"{CONFIG['company']['email']}",
            styles['BodyPara'])]
    ]
    prep_table = Table(prep_data, colWidths=[3.25*inch, 3.25*inch])
    prep_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(prep_table)
    story.append(Spacer(1, 15))

    # Date box
    date_data = [[Paragraph(f"<b>Date:</b> {date_str}", styles['CenterText'])]]
    date_table = Table(date_data, colWidths=[6.5*inch])
    date_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BLUE),
        ('BOX', (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(date_table)

    # ===== EXECUTIVE SUMMARY =====
    story.append(Paragraph("EXECUTIVE SUMMARY", styles['SectionHeader']))
    story.append(Paragraph(
        "Enter your executive summary here. This should provide a high-level overview "
        "of the proposed project, key benefits, and expected outcomes.",
        styles['BodyPara']))

    # ===== PROJECT SCOPE =====
    story.append(PageBreak())
    story.append(Paragraph("PROJECT SCOPE", styles['SectionHeader']))

    story.append(Paragraph("1. Phase One", styles['SubsectionHeader']))
    story.append(Paragraph("\u2022 <b>Task 1:</b> Description of first phase work item", styles['BulletItem']))
    story.append(Paragraph("\u2022 <b>Task 2:</b> Description of second work item", styles['BulletItem']))

    story.append(Paragraph("2. Phase Two", styles['SubsectionHeader']))
    story.append(Paragraph("\u2022 <b>Task 1:</b> Description of phase two work", styles['BulletItem']))

    # ===== INVESTMENT =====
    story.append(Paragraph("INVESTMENT", styles['SectionHeader']))

    inv_data = [
        [Paragraph("<b>Service</b>", styles['TableHeader']),
         Paragraph("<b>Hours</b>", styles['TableHeader']),
         Paragraph("<b>Rate</b>", styles['TableHeader']),
         Paragraph("<b>Subtotal</b>", styles['TableHeader'])],
        ["Service Line 1", "8", "$100/hr", "$800.00"],
        [Paragraph("<b>TOTAL</b>", styles['TableHeader']), "", "",
         Paragraph("<b>$800.00</b>", styles['TableHeader'])]
    ]
    inv_table = Table(inv_data, colWidths=[2.8*inch, 1*inch, 1*inch, 1.7*inch])
    inv_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ('BACKGROUND', (0, 2), (-1, 2), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 2), (-1, 2), HexColor("#FFFFFF")),
        ('BOX', (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    story.append(inv_table)

    # ===== TERMS =====
    story.append(Paragraph("TERMS & CONDITIONS", styles['SectionHeader']))
    terms_data = [[Paragraph(
        "<b>Payment:</b> 50% deposit to commence work, balance due within 30 days of completion<br/>"
        f"<b>Validity:</b> This proposal is valid for {CONFIG['proposal']['valid_days']} days<br/>"
        "<b>Warranty:</b> 30-day warranty on all work delivered",
        styles['BodyPara'])]]
    terms_table = Table(terms_data, colWidths=[6.5*inch])
    terms_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor("#F5F5F5")),
        ('BOX', (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
    ]))
    story.append(terms_table)

    # ===== SIGNATURE =====
    story.append(Spacer(1, 30))
    story.append(Paragraph("ACCEPTANCE", styles['SectionHeader']))
    story.append(Paragraph(
        "By signing below, both parties agree to the terms and scope outlined in this proposal.",
        styles['BodyPara']))
    story.append(Spacer(1, 20))

    sig_data = [
        [Paragraph("<b>Customer</b>", styles['BodyPara']),
         Paragraph(f"<b>{CONFIG['company']['name']}</b>", styles['BodyPara'])],
        ["", ""],
        [Paragraph("_" * 28, styles['BodyPara']),
         Paragraph("_" * 28, styles['BodyPara'])],
        [Paragraph("Signature / Date", styles['SmallText']),
         Paragraph("Signature / Date", styles['SmallText'])],
    ]
    sig_table = Table(sig_data, colWidths=[3.25*inch, 3.25*inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)

    # Build PDF
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"PDF created: {output_path}")


if __name__ == "__main__":
    output_file = sys.argv[1] if len(sys.argv) > 1 else "proposal.pdf"
    create_proposal(output_file)
