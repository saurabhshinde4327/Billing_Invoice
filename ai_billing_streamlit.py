import streamlit as st
from sqlalchemy import create_engine, text
from io import BytesIO
import os
import datetime
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import ast
from PIL import Image
from num2words import num2words
import plotly.express as px

# -------------------------------
# CONFIG
# -------------------------------
DB_USER = os.getenv("DB_USER", "test")
DB_PASS = os.getenv("DB_PASS", "test123")
DB_HOST = os.getenv("DB_HOST", "91.108.105.168")
DB_NAME = os.getenv("DB_NAME", "invoice")
LOGO_PATH = "Logo.jpg"

# -------------------------------
# DB SETUP
# -------------------------------
engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}")

def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_number VARCHAR(50),
                customer_name VARCHAR(255),
                customer_address TEXT,
                items TEXT,
                subtotal DECIMAL(10,2),
                cgst_rate DECIMAL(5,2),
                sgst_rate DECIMAL(5,2),
                discount DECIMAL(10,2),
                total DECIMAL(10,2),
                company_name VARCHAR(255) DEFAULT 'Data Center',
                company_address TEXT DEFAULT 'Yashavantrao Chavan Institute of Science, Satara',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

# -------------------------------
# PDF GENERATION
# -------------------------------
def generate_invoice_pdf(values, parsed_items, logo_path=None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    try:
        pdfmetrics.registerFont(TTFont('NotoSans', 'NotoSans-Regular.ttf'))
        pdfmetrics.registerFont(TTFont('NotoSans-Bold', 'NotoSans-Bold.ttf'))
        font_name = 'NotoSans'
        font_bold = 'NotoSans-Bold'
    except:
        font_name = 'Helvetica'
        font_bold = 'Helvetica-Bold'

    margin = 50
    y_pos = height - margin

    # Logo
    if logo_path and os.path.exists(logo_path):
        with Image.open(logo_path) as img:
            max_width, max_height = 80, 50
            img_width, img_height = img.size
            ratio = min(max_width/img_width, max_height/img_height)
            img = img.resize((int(img_width*ratio), int(img_height*ratio)), Image.Resampling.LANCZOS)
            img_reader = ImageReader(img)
            c.drawImage(img_reader, margin, y_pos - img.height, width=img.width, height=img.height, mask='auto')

    # Company Info
    x_text_start = margin + 100
    c.setFont(font_bold, 20)
    c.drawString(x_text_start, y_pos - 10, values.get('company_name', 'Data Center'))
    c.setFont(font_name, 12)
    for i, line in enumerate(values.get('company_address', 'Yashavantrao Chavan Institute of Science\nSatara').split('\n')):
        c.drawString(x_text_start, y_pos - 28 - i*15, line)
    y_pos -= 70

    # Invoice number & date
    c.setFont(font_bold, 14)
    c.drawRightString(width - margin, height - margin - 40, f"INVOICE: {values.get('invoice_number','')}")
    c.setFont(font_name, 10)
    c.drawRightString(width - margin, height - margin - 55, f"Date: {datetime.datetime.now().strftime('%d-%b-%Y')}")

    # Customer info
    c.setFont(font_bold, 12)
    c.drawString(margin, y_pos, "BILL TO:")
    y_pos -= 15
    c.setFont(font_name, 10)
    c.drawString(margin, y_pos, values['customer_name'])
    y_pos -= 12
    for line in values['customer_address'].split('\n'):
        c.drawString(margin, y_pos, line)
        y_pos -= 12

    # Table header
    y_pos -= 20
    c.setFont(font_bold, 10)
    c.drawString(margin, y_pos, "DESCRIPTION")
    c.drawRightString(width - margin - 220, y_pos, "QTY")
    c.drawRightString(width - margin - 120, y_pos, "PRICE")
    c.drawRightString(width - margin, y_pos, "TOTAL")
    y_pos -= 10
    c.line(margin, y_pos, width - margin, y_pos)
    y_pos -= 12

    # Items
    c.setFont(font_name, 10)
    subtotal = 0
    desc_width = 250

    for item, qty, price in parsed_items:
        total = float(qty) * float(price)
        subtotal += total

        words = str(item).split()
        line = ""
        first_line_y = y_pos
        for word in words:
            test_line = line + " " + word if line else word
            if c.stringWidth(test_line, font_name, 10) <= desc_width:
                line = test_line
            else:
                c.drawString(margin, y_pos, line)
                y_pos -= 12
                line = word
        if line:
            c.drawString(margin, y_pos, line)

        c.drawRightString(width - margin - 220, first_line_y, f"{qty:.2f}")
        c.drawRightString(width - margin - 120, first_line_y, f"{price:,.2f}")
        c.drawRightString(width - margin, first_line_y, f"{total:,.2f}")

        y_pos -= 15

    # Summary
    y_pos -= 10
    discount = float(values.get("discount") or 0)
    cgst_amt = subtotal * float(values.get("cgst_rate") or 0)/100
    sgst_amt = subtotal * float(values.get("sgst_rate") or 0)/100
    total_amount = subtotal + cgst_amt + sgst_amt - discount

    summary_x = width - margin - 200
    c.setFont(font_name, 10)
    c.drawRightString(summary_x + 150, y_pos, f"Subtotal: {subtotal:,.2f}")
    y_pos -= 15
    c.drawRightString(summary_x + 150, y_pos, f"CGST @{values.get('cgst_rate') or 0}%: {cgst_amt:,.2f}")
    y_pos -= 15
    c.drawRightString(summary_x + 150, y_pos, f"SGST @{values.get('sgst_rate') or 0}%: {sgst_amt:,.2f}")
    y_pos -= 15
    c.drawRightString(summary_x + 150, y_pos, f"Discount: {discount:,.2f}")
    y_pos -= 15
    c.setFont(font_bold, 12)
    c.drawRightString(summary_x + 150, y_pos, f"Total: {total_amount:,.2f}")

    # Total in words
    y_pos -= 20
    total_words = num2words(total_amount, to='currency', lang='en_IN')
    total_words = total_words.replace('euro', 'Rupees').replace('cents', 'Paise')
    c.setFont(font_name, 10)
    c.drawString(margin, y_pos, f"Total (in words): {total_words.capitalize()} only")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# -------------------------------
# STREAMLIT APP
# -------------------------------
st.set_page_config(page_title="Invoice System", layout="wide", page_icon="🧾")
st.title("Invoice Management System")

page = st.sidebar.radio("Navigate", ["Create Invoice", "Invoice History", "Dashboard"])

# 🔄 Auto-refresh every 10 seconds
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=10 * 1000, key=f"refresh_{page}")


init_db()

# -------------------------------
# CREATE INVOICE
# -------------------------------
if page == "Create Invoice":
    st.subheader("Create New Invoice")

    invoice_number = st.text_input("Invoice Number (Enter Manually)", "")

    col1, col2 = st.columns([2,3])
    with col1:
        st.text_input("Company Name", value="Data Center", key="company_name")
        st.text_area("Company Address", value="Yashavantrao Chavan Institute of Science Satara", key="company_address", height=80)
    with col2:
        customer_name = st.text_input("Customer Name")
        customer_address = st.text_area("Customer Address", height=80)

    st.markdown("**Invoice Items** (format: description | qty | price per line)")
    items_input = st.text_area("", height=150, placeholder="Laptop Dell | 1 | 50000")

    col3, col4, col5 = st.columns(3)
    with col3:
        discount = st.number_input("Discount (₹)", value=0.0)
    with col4:
        cgst = st.number_input("CGST %", value=9.0)
    with col5:
        sgst = st.number_input("SGST %", value=9.0)

    if st.button("Generate & Save Invoice"):
        if not invoice_number or not customer_name or not customer_address or not items_input:
            st.error("Please fill all fields including Invoice Number!")
        else:
            parsed_items = []
            for line in items_input.split("\n"):
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 3:
                    st.error("Each item must follow format: description | qty | price")
                    st.stop()
                desc = "|".join(parts[:-2])
                qty = float(parts[-2])
                price = float(parts[-1])
                parsed_items.append((desc, qty, price))

            subtotal = sum(qty*price for _, qty, price in parsed_items)
            cgst_amt = subtotal*cgst/100
            sgst_amt = subtotal*sgst/100
            total = subtotal + cgst_amt + sgst_amt - discount

            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO invoices
                    (invoice_number, customer_name, customer_address, items, subtotal, cgst_rate, sgst_rate, discount, total, company_name, company_address)
                    VALUES (:inv, :cname, :caddr, :items, :subtotal, :cgst, :sgst, :discount, :total, :company_name, :company_address)
                """), {
                    "inv": invoice_number,
                    "cname": customer_name,
                    "caddr": customer_address,
                    "items": str(parsed_items),
                    "subtotal": subtotal,
                    "cgst": cgst,
                    "sgst": sgst,
                    "discount": discount,
                    "total": total,
                    "company_name": "Data Center",
                    "company_address": "Yashavantrao Chavan Institute of Science\nSatara"
                })

            pdf_bytes = generate_invoice_pdf({
                "invoice_number": invoice_number,
                "customer_name": customer_name,
                "customer_address": customer_address,
                "discount": discount,
                "cgst_rate": cgst,
                "sgst_rate": sgst,
                "company_name": "Data Center",
                "company_address": "Yashavantrao Chavan Institute of Science\nSatara"
            }, parsed_items, logo_path=LOGO_PATH)

            st.success(f"Invoice {invoice_number} saved successfully!")
            st.download_button("Download Invoice PDF", pdf_bytes, file_name=f"Invoice_{invoice_number}.pdf", mime="application/pdf")

# -------------------------------
# INVOICE HISTORY
# -------------------------------
elif page == "Invoice History":
    st.subheader("Invoice History")
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT * FROM invoices ORDER BY created_at DESC")).mappings().all()
    if rows:
        df = pd.DataFrame(rows)
        df['created_at'] = df['created_at'].apply(lambda x: x.strftime("%d %b %Y %H:%M") if x else "")
        display_df = df[['invoice_number','customer_name','created_at','total']].copy()
        display_df.rename(columns={'invoice_number':'Invoice No','customer_name':'Customer','created_at':'Date','total':'Total (₹)'}, inplace=True)
        st.dataframe(display_df,use_container_width=True)

        selected_invoice = st.selectbox("Select Invoice", df['invoice_number'].tolist())
        if selected_invoice:
            selected_row = df[df['invoice_number']==selected_invoice].iloc[0]
            parsed_items = []
            if selected_row["items"]:
                try:
                    items_from_db = ast.literal_eval(selected_row["items"])
                    for itm in items_from_db:
                        if len(itm) == 3:
                            parsed_items.append((itm[0], float(itm[1]), float(itm[2])))
                except:
                    st.error("Error reading items from database")

            pdf_bytes = generate_invoice_pdf({
                "invoice_number": selected_row["invoice_number"],
                "customer_name": selected_row["customer_name"],
                "customer_address": selected_row["customer_address"],
                "discount": float(selected_row.get("discount") or 0),
                "cgst_rate": float(selected_row.get("cgst_rate") or 0),
                "sgst_rate": float(selected_row.get("sgst_rate") or 0),
                "company_name": selected_row.get("company_name", "Data Center"),
                "company_address": selected_row.get("company_address", "Yashavantrao Chavan Institute of Science\nSatara")
            }, parsed_items, logo_path=LOGO_PATH)

            col1, col2 = st.columns(2)
            with col1:
                st.download_button("Download Invoice PDF", pdf_bytes, file_name=f"Invoice_{selected_invoice}.pdf", mime="application/pdf")
            with col2:
                if st.button("🗑️ Delete Invoice"):
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM invoices WHERE invoice_number=:inv"), {"inv":selected_invoice})
                    st.success(f"Invoice {selected_invoice} deleted successfully!")

# -------------------------------
# DASHBOARD
# -------------------------------
elif page == "Dashboard":
    st.subheader("Dashboard")
    with engine.begin() as conn:
        total_invoices = conn.execute(text("SELECT COUNT(*) FROM invoices")).scalar() or 0
        total_revenue = conn.execute(text("SELECT SUM(total) FROM invoices")).scalar() or 0
        avg_invoice = conn.execute(text("SELECT AVG(total) FROM invoices")).scalar() or 0

        df = pd.read_sql("SELECT invoice_number, customer_name, total, created_at FROM invoices ORDER BY created_at", conn)

    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Invoices", total_invoices)
    col2.metric("Total Revenue (₹)", f"{total_revenue:,.2f}")
    col3.metric("Average Invoice (₹)", f"{avg_invoice:,.2f}")

    if not df.empty:
        df['created_at'] = pd.to_datetime(df['created_at'])
        df['date'] = df['created_at'].dt.date

        # 🎯 Graph selection
        graph_options = ["Daily Revenue Trend", "Top Customers", "Revenue Share (Pie)", "Monthly Revenue"]
        selected_graphs = st.multiselect("Select Graphs to Display", graph_options, default=graph_options[:2])

        if "Daily Revenue Trend" in selected_graphs:
            st.markdown("📊 Revenue Over Time")
            revenue_over_time = df.groupby('date')['total'].sum().reset_index()
            fig_line = px.line(revenue_over_time, x='date', y='total',
                               title="Daily Revenue", markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

        if "Top Customers" in selected_graphs:
            st.markdown("📊 Revenue by Customer (Top 10)")
            top_customers = df.groupby('customer_name')['total'].sum().nlargest(10).reset_index()
            fig_bar = px.bar(top_customers, x='customer_name', y='total',
                             title="Top Customers", text_auto='.2s')
            st.plotly_chart(fig_bar, use_container_width=True)

        if "Revenue Share (Pie)" in selected_graphs:
            st.markdown("📊 Invoice Distribution")
            fig_pie = px.pie(df, names='customer_name', values='total',
                             title="Revenue Share by Customer")
            st.plotly_chart(fig_pie, use_container_width=True)

        if "Monthly Revenue" in selected_graphs:
            st.markdown("📊 Monthly Revenue")
            df['month'] = df['created_at'].dt.to_period('M').astype(str)
            monthly_revenue = df.groupby('month')['total'].sum().reset_index()
            fig_month = px.bar(monthly_revenue, x='month', y='total',
                               title="Revenue per Month", text_auto='.2s')
            st.plotly_chart(fig_month, use_container_width=True)

    else:
        st.info("No invoices available to display graphs.")
