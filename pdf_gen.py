# pdf_gen.py
import datetime
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Font Registration
def register_fonts():
    try:
        pdfmetrics.registerFont(TTFont("Inter-Regular", "Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "Inter-Bold.ttf"))
        return {'regular': "Inter-Regular", 'bold': "Inter-Bold"}
    except Exception:
        return {'regular': "Helvetica", 'bold': "Helvetica-Bold"}

FONTS = register_fonts()

# Color Scheme
class InvoiceColors:
    PRIMARY = colors.HexColor("#2D3748")
    BORDER = colors.HexColor("#E2E8F0")
    TEXT = colors.HexColor("#2D3748")
    WHITE = colors.white

# Styles
class ModernStyles:
    @staticmethod
    def get_styles():
        styles = {}
        styles['invoice_title'] = ParagraphStyle(
            'invoice_title', fontName=FONTS['bold'], fontSize=18, leading=22,
            textColor=InvoiceColors.PRIMARY, alignment=TA_CENTER)
        styles['company_name'] = ParagraphStyle(
            'company_name', fontName=FONTS['bold'], fontSize=20, leading=24,
            textColor=InvoiceColors.PRIMARY, alignment=TA_LEFT)
        styles['company_tagline'] = ParagraphStyle(
            'company_tagline', fontName=FONTS['bold'], fontSize=12, leading=14,
            textColor=InvoiceColors.PRIMARY, alignment=TA_LEFT)
        styles['doc_info'] = ParagraphStyle(
            'doc_info', fontName=FONTS['regular'], fontSize=10, leading=12,
            textColor=InvoiceColors.TEXT, alignment=TA_RIGHT)
        styles['invoice_to'] = ParagraphStyle(
            'invoice_to', fontName=FONTS['regular'], fontSize=11, leading=14,
            textColor=InvoiceColors.TEXT)
        styles['normal'] = ParagraphStyle(
            'normal', fontName=FONTS['regular'], fontSize=10, leading=12,
            textColor=InvoiceColors.TEXT)
        styles['bold'] = ParagraphStyle(
            'bold', fontName=FONTS['bold'], fontSize=10, leading=12,
            textColor=InvoiceColors.TEXT)
        styles['terms'] = ParagraphStyle(
            'terms', fontName=FONTS['regular'], fontSize=10, leading=13,
            textColor=InvoiceColors.TEXT)
        return styles

# Number to Words
def number_to_words(amount):
    def convert_hundreds(num):
        ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
                'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
                'seventeen', 'eighteen', 'nineteen']
        tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
        result = ''
        if num >= 100:
            result += ones[num // 100] + ' hundred '
            num %= 100
        if num >= 20:
            result += tens[num // 10]
            if num % 10 != 0:
                result += ' ' + ones[num % 10]
        elif num > 0:
            result += ones[num]
        return result.strip()

    if amount == 0: return "Zero Rupees Only"
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    result = ""
    if rupees >= 10000000:
        crores = rupees // 10000000
        result += convert_hundreds(crores) + " crore "
        rupees %= 10000000
    if rupees >= 100000:
        lakhs = rupees // 100000
        result += convert_hundreds(lakhs) + " lakh "
        rupees %= 100000
    if rupees >= 1000:
        thousands = rupees // 1000
        result += convert_hundreds(thousands) + " thousand "
        rupees %= 1000
    if rupees > 0:
        result += convert_hundreds(rupees) + " "
    if result.strip():
        result += "rupees"
    if paise > 0:
        if result.strip(): result += " and "
        result += convert_hundreds(paise) + " paise"
    result += " only"
    return result.strip().title()

# Logo Handler
def add_logo(logo_path, max_width=80, max_height=80):
    try:
        if os.path.exists(logo_path):
            img = Image(logo_path)
            scale = min(max_width / img.imageWidth, max_height / img.imageHeight)
            img.drawWidth = img.imageWidth * scale
            img.drawHeight = img.imageHeight * scale
            return img
    except Exception as e:
        print(f"Could not load logo: {e}")
    return None

# PDF Generator
def generate_simple_invoice_pdf(values: dict, items: list):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    story = []
    styles = ModernStyles.get_styles()

    # Invoice Title
    story.append(Paragraph("INVOICE", styles['invoice_title']))
    story.append(Spacer(1, 10))

    # Company Logo & Name
    company_name = values.get('company_name', 'Data Center')
    company_tagline = "Yashavantrao Chavan Institute of Science"
    logo = add_logo(values.get('logo_path', 'Logo.jpg'))
    if logo:
        header_table = Table([
            [logo, Spacer(1,5), Paragraph(f"<b>{company_name}</b><br/>{company_tagline}", styles['company_tagline'])]
        ], colWidths=[80, 10, 350])
        header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        story.append(header_table)
    else:
        story.append(Paragraph(f"<b>{company_name}</b>", styles['company_name']))
        story.append(Paragraph(company_tagline, styles['company_tagline']))
    story.append(Spacer(1, 10))

    # Invoice # and Date (right aligned, date separate line)
    doc_number = values.get('doc_number', 'INV-001')
    doc_date = values.get('doc_date', datetime.datetime.now().strftime('%d/%m/%Y'))
    invoice_info_table = Table([
        ['', Paragraph(f"<b>Invoice #:</b> {doc_number}<br/><b>Date:</b> {doc_date}", styles['doc_info'])]
    ], colWidths=[350, 120])
    invoice_info_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (1,0), (1,0), 0),
        ('RIGHTPADDING', (1,0), (1,0), 0)
    ]))
    story.append(invoice_info_table)
    story.append(Spacer(1, 15))

    # Customer Info
    customer_name = values.get('customer_name', 'Customer Name')
    customer_address = values.get('customer_address', 'Customer Address')
    story.append(Paragraph(f"<b>Invoice to:</b><br/><b>{customer_name}</b><br/>{customer_address}", styles['invoice_to']))
    story.append(Spacer(1, 15))

    # Items Table
    table_data = [["No", "Item Description", "Qty", "Price", "Total"]]
    subtotal = 0
    for i, (desc, qty, rate) in enumerate(items, start=1):
        total = qty * rate
        subtotal += total
        table_data.append([str(i), Paragraph(desc, styles['normal']), f"{qty:g}", f"{rate:,.2f}", f"{total:,.2f}"])

    items_table = Table(table_data, colWidths=[30, 220, 40, 70, 90], repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), InvoiceColors.PRIMARY),
        ('TEXTCOLOR', (0,0), (-1,0), InvoiceColors.WHITE),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('ALIGN', (2,0), (2,-1), 'CENTER'),
        ('ALIGN', (3,0), (4,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 1, InvoiceColors.BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, InvoiceColors.BORDER),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))

    # Totals
    cgst = float(values.get('cgst_rate', 0))
    sgst = float(values.get('sgst_rate', 0))
    discount = float(values.get('discount', 0))
    cgst_amt = subtotal * cgst / 100
    sgst_amt = subtotal * sgst / 100
    total_tax = cgst_amt + sgst_amt
    grand_total = subtotal + total_tax - discount

    totals_data = [["Sub Total", f"{subtotal:,.2f}"]]
    if cgst>0: totals_data.append([f"CGST @ {cgst}%", f"{cgst_amt:,.2f}"])
    if sgst>0: totals_data.append([f"SGST @ {sgst}%", f"{sgst_amt:,.2f}"])
    if discount>0: totals_data.append(["Discount", f"- {discount:,.2f}"])
    totals_data.extend([["Tax", f"{total_tax:,.2f}"], ["TOTAL", f"{grand_total:,.2f}"]])

    totals_table = Table(totals_data, colWidths=[120,90], hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,-1), (-1,-1), FONTS['bold']),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOX', (0,0), (-1,-1), 1, InvoiceColors.BORDER),
        ('INNERGRID', (0,0), (-1,-2), 0.5, InvoiceColors.BORDER),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 10))

    # Amount in words
    story.append(Paragraph(f"<b>Amount in Words:</b> {number_to_words(grand_total)}", styles['bold']))
    story.append(Spacer(1, 10))

    # Terms
    terms_text = """
    <b>Terms and Conditions:</b><br/>
    1. Validity: Quotation valid for 30 days.<br/>
    2. Service Duration: 12 months from date of activation.<br/>
    3. Support Includes: Regular updates, monitoring and priority issue resolution.
    """
    story.append(Paragraph(terms_text, styles['terms']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Backward Compatibility
def generate_professional_pdf(values: dict, items: list, doc_type: str = "INVOICE"):
    return generate_simple_invoice_pdf(values, items)

# Example Test
if __name__ == "__main__":
    values = {
        'company_name': 'Data Center',
        'doc_number': 'DC0001',
        'doc_date': '31/08/2025',
        'customer_name': 'The Secretary',
        'customer_address': "Rayat Shikshan Sanstha's, Maharashtra, Satara 415002",
        'cgst_rate': 0.0,
        'sgst_rate': 0.0,
        'discount': 0,
        'logo_path': 'Logo.jpg'
    }
    items = [("KVM 1 Hosting Server: 2 vCPU, 4 GB Memory, 50 GB SSD Disk Storage, Security and Backup, Technical Support", 1, 15158.00)]

    pdf_bytes = generate_simple_invoice_pdf(values, items)
    with open("invoice_no_rupees.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("Invoice generated: invoice_no_rupees.pdf")
