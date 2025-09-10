import datetime
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

# --------------------------
# Font Registration
# --------------------------
def register_fonts():
    try:
        pdfmetrics.registerFont(TTFont("Inter-Regular", "Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "Inter-Bold.ttf"))
        return {'regular': "Inter-Regular", 'bold': "Inter-Bold"}
    except Exception:
        return {'regular': "Helvetica", 'bold': "Helvetica-Bold"}

FONTS = register_fonts()

# --------------------------
# Color Scheme
# --------------------------
class InvoiceColors:
    PRIMARY = colors.HexColor("#2D3748")
    BORDER = colors.HexColor("#E2E8F0")
    TEXT = colors.HexColor("#2D3748")
    WHITE = colors.white

# --------------------------
# Styles
# --------------------------
class ModernStyles:
    @staticmethod
    def get_styles():
        styles = {}
        styles['invoice_title'] = ParagraphStyle('invoice_title', fontName=FONTS['bold'], fontSize=18, leading=22, textColor=InvoiceColors.PRIMARY, alignment=TA_CENTER)
        styles['company_name'] = ParagraphStyle('company_name', fontName=FONTS['bold'], fontSize=20, leading=24, textColor=InvoiceColors.PRIMARY, alignment=TA_LEFT)
        styles['company_tagline'] = ParagraphStyle('company_tagline', fontName=FONTS['bold'], fontSize=12, leading=14, textColor=InvoiceColors.PRIMARY, alignment=TA_LEFT)
        styles['doc_info'] = ParagraphStyle('doc_info', fontName=FONTS['regular'], fontSize=10, leading=12, textColor=InvoiceColors.TEXT, alignment=TA_RIGHT)
        styles['To,'] = ParagraphStyle('To,', fontName=FONTS['regular'], fontSize=11, leading=14, textColor=InvoiceColors.TEXT)
        styles['normal'] = ParagraphStyle('normal', fontName=FONTS['regular'], fontSize=10, leading=12, textColor=InvoiceColors.TEXT)
        styles['bold'] = ParagraphStyle('bold', fontName=FONTS['bold'], fontSize=10, leading=12, textColor=InvoiceColors.TEXT)
        styles['terms'] = ParagraphStyle('terms', fontName=FONTS['regular'], fontSize=10, leading=13, textColor=InvoiceColors.TEXT)
        return styles

# --------------------------
# Number to Words
# --------------------------
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

    if amount == 0:
        return "Zero Rupees Only"
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

# --------------------------
# Logo Handler
# --------------------------
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

# --------------------------
# Watermark
# --------------------------
def watermark(canvas_obj, doc, logo_path):
    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            page_width, page_height = A4
            img_width, img_height = 200, 200
            x = (page_width - img_width) / 2
            y = (page_height - img_height) / 2
            canvas_obj.saveState()
            canvas_obj.setFillAlpha(0.1)
            canvas_obj.drawImage(img, x, y, width=img_width, height=img_height, mask='auto')
            canvas_obj.restoreState()
        except Exception as e:
            print(f"Watermark error: {e}")

# --------------------------
# PDF Generator
# --------------------------
def generate_simple_invoice_pdf(values: dict, items: list):
    buffer = BytesIO()
    logo_path = values.get('logo_path', 'Logo.jpg')
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    story = []
    styles = ModernStyles.get_styles()

    # Title
    story.append(Paragraph("INVOICE", styles['invoice_title']))
    story.append(Spacer(1, 10))

    # Logo + Company
    company_name = values.get('company_name', 'Data Center')
    company_tagline = "Yashavantrao Chavan Institute of Science, Satara."
    logo = add_logo(logo_path)
    if logo:
        header_table = Table([[logo, Spacer(1,5), Paragraph(f"<b>{company_name}</b><br/>{company_tagline}", styles['company_tagline'])]], colWidths=[80,10,350])
        header_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
        story.append(header_table)
    else:
        story.append(Paragraph(f"<b>{company_name}</b>", styles['company_name']))
        story.append(Paragraph(company_tagline, styles['company_tagline']))
    story.append(Spacer(1, 10))

    # Invoice info
    doc_number = values.get('doc_number','INV-001')
    doc_date = values.get('doc_date', datetime.datetime.now().strftime('%d/%m/%Y'))
    invoice_info = Table([['', Paragraph(f"<b>Invoice #:</b> {doc_number}<br/><b>Date:</b> {doc_date}", styles['doc_info'])]], colWidths=[350,120])
    invoice_info.setStyle(TableStyle([('ALIGN',(1,0),(1,0),'RIGHT')]))
    story.append(invoice_info)
    story.append(Spacer(1, 15))

    # Customer Info
    customer_name = values.get('customer_name','Customer Name')
    customer_address = values.get('customer_address','Customer Address')
    story.append(Paragraph(f"<b>To,</b><br/><b>{customer_name}</b><br/>{customer_address}", styles['To,']))
    story.append(Spacer(1, 15))

    # Items
    table_data = [["No","Item Description","Qty","Price","Total"]]
    subtotal = 0
    for i,(desc,qty,rate) in enumerate(items,start=1):
        total = qty*rate
        subtotal += total
        table_data.append([str(i), Paragraph(desc, styles['normal']), f"{qty:g}", f"{rate:,.2f}", f"{total:,.2f}"])
    table = Table(table_data,colWidths=[30,220,40,70,90],repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),InvoiceColors.PRIMARY),
        ('TEXTCOLOR',(0,0),(-1,0),InvoiceColors.WHITE),

        # Alignments
        ('ALIGN',(0,0),(0,-1),'CENTER'),   # Sr No
        ('ALIGN',(1,0),(1,-1),'LEFT'),     # Item Description
        ('ALIGN',(2,0),(2,-1),'CENTER'),   # Qty
        ('ALIGN',(3,0),(3,-1),'CENTER'),   # Price
        ('ALIGN',(4,0),(4,-1),'CENTER'),   # Total

        # Vertical alignment fix
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),

        # Borders
        ('BOX',(0,0),(-1,-1),1,InvoiceColors.BORDER),
        ('INNERGRID',(0,0),(-1,-1),0.5,InvoiceColors.BORDER),
    ]))
    story.append(table)
    story.append(Spacer(1, 15))

    # Totals
    cgst = float(values.get('cgst_rate',0))
    sgst = float(values.get('sgst_rate',0))
    discount = float(values.get('discount',0))
    cgst_amt = subtotal*cgst/100
    sgst_amt = subtotal*sgst/100
    total_tax = cgst_amt+sgst_amt
    grand_total = subtotal+total_tax-discount

    totals=[["Sub Total",f"{subtotal:,.2f}"]]
    if cgst>0: totals.append([f"CGST @ {cgst}%",f"{cgst_amt:,.2f}"])
    if sgst>0: totals.append([f"SGST @ {sgst}%",f"{sgst_amt:,.2f}"])
    if discount>0: totals.append(["Discount",f"- {discount:,.2f}"])
    totals.extend([["Tax",f"{total_tax:,.2f}"],["TOTAL",f"{grand_total:,.2f}"]])
    totals_table=Table(totals,colWidths=[120,90],hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('ALIGN',(0,0),(0,-1),'LEFT'),
        ('ALIGN',(1,0),(1,-1),'RIGHT'),
        ('FONTNAME',(0,-1),(-1,-1),FONTS['bold']),
        ('BOX',(0,0),(-1,-1),1,InvoiceColors.BORDER),
        ('INNERGRID',(0,0),(-1,-2),0.5,InvoiceColors.BORDER),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),   # Vertical align totals table too
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 10))

    # Amount in words
    story.append(Paragraph(f"<b>Amount in Words:</b> {number_to_words(grand_total)}", styles['bold']))
    story.append(PageBreak())

    # Terms on new page
    terms_text = """
    <b>Terms and Conditions:</b><br/>
•	These terms remain binding unless otherwise agreed in writing under a Service Level Agreement (SLA) or other executed agreement.<br/>
•	Payments must be made within the agreed terms from the invoice date.<br/>
•	Delayed payments will attract interest at 2% per month until realization.<br/>
•	Back-to-back payment terms are acceptable only if mutually agreed in writing.<br/>
•	All payments shall be made in Indian Rupees (INR) in favor of YCIS Data Center.<br/>
•	Any dispute regarding invoice amount, services, or products must be raised in writing within 7 days of receipt.<br/>
•	No claims will be entertained after this period.<br/>
•	If a Proforma Invoice is issued, it will automatically convert into a Tax Invoice and be binding if no objection is raised within 7 days of receipt.<br/>
•	Services may be suspended, discontinued, or terminated in case of non-payment.<br/>
•	Suspension or termination of services due to non-payment shall not be considered a breach of SLA.<br/>
•	Suspended services will resume only after full settlement of all outstanding dues.<br/>
•	YCIS Data Center will not be liable for any loss or damage caused due to service suspension, degradation, termination, or client-side issues.<br/>
•	Timely payment is essential to ensure uninterrupted services and enables YCIS Data Center to maintain infrastructure and resources.<br/>

    """
    story.append(Paragraph(terms_text, styles['terms']))

    def on_page(c, d):
        watermark(c,d,logo_path)

    doc.build(story,onFirstPage=on_page,onLaterPages=on_page)
    buffer.seek(0)
    return buffer.getvalue()

# --------------------------
# Backward Compatibility
# --------------------------
def generate_professional_pdf(values, items, doc_type="INVOICE"):
    return generate_simple_invoice_pdf(values, items)
