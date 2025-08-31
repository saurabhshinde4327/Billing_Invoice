# app.py
import os
import ast
import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import engine, init_db, delete_row
from utils import parse_items
from pdf_gen import generate_professional_pdf as generate_pdf_bytes

# -----------------------
# Streamlit Page Config
# -----------------------
st.set_page_config(page_title="Invoice & Quotation System", layout="wide", page_icon="🧾")
st.title("Invoice & Quotation System")

from streamlit_autorefresh import st_autorefresh
page = st.sidebar.radio("Navigate", ["Create Invoice", "Invoice History", "Create Quotation", "Quotation History", "Dashboard"])
st_autorefresh(interval=8 * 1000, key=f"refresh_{page}")

# Initialize DB
try:
    init_db()
except Exception as e:
    st.error("Database initialization failed. Check DB connection.")
    st.exception(e)

# -----------------------
# Create Invoice
# -----------------------
if page == "Create Invoice":
    st.subheader("Create New Invoice (Blue)")
    inv_no = st.text_input("Invoice Number")
    col1, col2 = st.columns([2,3])
    with col1:
        company_name = st.text_input("Company Name", value="Data Center")
        company_address = st.text_area("Company Address", value="Yashavantrao Chavan Institute of Science\nSatara", height=80)
    with col2:
        cust_name = st.text_input("Customer Name")
        cust_addr = st.text_area("Customer Address", height=80)

    items_text = st.text_area("Items — description | qty | price", height=220, placeholder="Description | qty | price")
    c1, c2, c3 = st.columns(3)
    with c1:
        discount = st.number_input("Discount (₹)", value=0.0, min_value=0.0)
    with c2:
        cgst = st.number_input("CGST %", value=0.0, min_value=0.0)
    with c3:
        sgst = st.number_input("SGST %", value=0.0, min_value=0.0)

    if st.button("Generate & Save Invoice"):
        if not (inv_no and cust_name and cust_addr and items_text.strip()):
            st.error("Fill Invoice No, Customer & Items.")
        else:
            items = parse_items(items_text)
            subtotal = sum(q * p for _, q, p in items)
            total = subtotal + subtotal * cgst/100 + subtotal * sgst/100 - discount
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO invoices
                        (invoice_number, customer_name, customer_address, items, subtotal, cgst_rate, sgst_rate, discount, total, company_name, company_address)
                        VALUES (:inv,:cname,:caddr,:items,:sub,:cgst,:sgst,:disc,:tot,:comp,:caddr2)
                    """), {
                        "inv": inv_no, "cname": cust_name, "caddr": cust_addr,
                        "items": str(items), "sub": subtotal,
                        "cgst": cgst, "sgst": sgst, "disc": discount, "tot": total,
                        "comp": company_name, "caddr2": company_address
                    })
                pdf_bytes = generate_pdf_bytes({
                    "doc_number": inv_no, "company_name": company_name, "company_address": company_address,
                    "customer_name": cust_name, "customer_address": cust_addr,
                    "cgst_rate": cgst, "sgst_rate": sgst, "discount": discount
                }, items, doc_type="INVOICE")
                st.success(f"Invoice {inv_no} saved.")
                st.download_button("⬇️ Download Invoice PDF", pdf_bytes, file_name=f"Invoice_{inv_no}.pdf", mime="application/pdf")
            except Exception as e:
                st.error("Failed saving invoice (duplicate number or DB error).")
                st.exception(e)

# -----------------------
# Invoice History
# -----------------------
elif page == "Invoice History":
    st.subheader("Invoice History")
    try:
        with engine.begin() as conn:
            rows = conn.execute(text("SELECT * FROM invoices ORDER BY created_at DESC")).mappings().all()
    except Exception as e:
        st.error("Failed reading invoices from DB.")
        st.exception(e)
        rows = []

    if rows:
        df = pd.DataFrame(rows)
        df['created_at'] = df['created_at'].apply(lambda x: x.strftime("%d %b %Y %H:%M") if x else "")
        st.dataframe(df[['invoice_number','customer_name','created_at','total']].rename(columns={
            'invoice_number':'Invoice No','customer_name':'Customer','created_at':'Date','total':'Total (₹)'
        }), use_container_width=True)

        selected = st.selectbox("Select Invoice", df['invoice_number'].tolist())
        if selected:
            row = df[df['invoice_number'] == selected].iloc[0]
            try:
                items = [(i[0], float(i[1]), float(i[2])) for i in ast.literal_eval(row["items"] or "[]")]
            except Exception:
                items = []
                st.error("Error parsing items from DB.")
            pdf_bytes = generate_pdf_bytes({
                "doc_number": row["invoice_number"], "company_name": row.get("company_name", "Data Center"),
                "company_address": row.get("company_address", ""), "customer_name": row.get("customer_name", ""),
                "customer_address": row.get("customer_address", ""), "cgst_rate": float(row.get("cgst_rate") or 0),
                "sgst_rate": float(row.get("sgst_rate") or 0), "discount": float(row.get("discount") or 0)
            }, items, doc_type="INVOICE")

            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                st.download_button("⬇️ Download PDF", pdf_bytes, file_name=f"Invoice_{selected}.pdf", mime="application/pdf")
            with c2:
                confirm = st.checkbox("Confirm delete")
            with c3:
                if st.button("❌ Delete Invoice") and confirm:
                    delete_row("invoices", "invoice_number", selected)
                    st.success(f"Invoice {selected} deleted.")
    else:
        st.info("No invoices yet.")

# -----------------------
# Create Quotation
# -----------------------
elif page == "Create Quotation":
    st.subheader("Create Quotation (Yellow)")
    q_no = st.text_input("Quotation Number")
    col1, col2 = st.columns([2,3])
    with col1:
        company_name = st.text_input("Company Name", value="Data Center", key="q_comp")
        company_address = st.text_area("Company Address", value="Yashavantrao Chavan Institute of Science\nSatara", height=80, key="q_comp_addr")
    with col2:
        cust_name = st.text_input("Customer Name", key="q_cust")
        cust_addr = st.text_area("Customer Address", height=80, key="q_addr")

    items_text = st.text_area("Items — description | qty | price", height=220, key="q_items")
    c1, c2, c3 = st.columns(3)
    with c1:
        discount = st.number_input("Discount (₹)", value=0.0, min_value=0.0, key="q_disc")
    with c2:
        cgst = st.number_input("CGST %", value=0.0, min_value=0.0, key="q_cgst")
    with c3:
        sgst = st.number_input("SGST %", value=0.0, min_value=0.0, key="q_sgst")

    if st.button("Generate & Save Quotation"):
        if not (q_no and cust_name and cust_addr and items_text.strip()):
            st.error("Fill Quotation number, customer & items.")
        else:
            items = parse_items(items_text)
            subtotal = sum(q * p for _, q, p in items)
            total = subtotal + subtotal * cgst/100 + subtotal * sgst/100 - discount
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO quotations
                        (quotation_number, customer_name, customer_address, items, subtotal, cgst_rate, sgst_rate, discount, total, company_name, company_address)
                        VALUES (:qno,:cname,:caddr,:items,:sub,:cgst,:sgst,:disc,:tot,:comp,:caddr2)
                    """), {
                        "qno": q_no, "cname": cust_name, "caddr": cust_addr,
                        "items": str(items), "sub": subtotal,
                        "cgst": cgst, "sgst": sgst, "disc": discount, "tot": total,
                        "comp": company_name, "caddr2": company_address
                    })
                pdf_bytes = generate_pdf_bytes({
                    "doc_number": q_no, "company_name": company_name, "company_address": company_address,
                    "customer_name": cust_name, "customer_address": cust_addr,
                    "cgst_rate": cgst, "sgst_rate": sgst, "discount": discount
                }, items, doc_type="QUOTATION")
                st.success(f"Quotation {q_no} saved.")
                st.download_button("⬇️ Download Quotation PDF", pdf_bytes, file_name=f"Quotation_{q_no}.pdf", mime="application/pdf")
            except Exception as e:
                st.error("Failed saving quotation.")
                st.exception(e)

# -----------------------
# Quotation History
# -----------------------
elif page == "Quotation History":
    st.subheader("Quotation History")
    try:
        with engine.begin() as conn:
            rows = conn.execute(text("SELECT * FROM quotations ORDER BY created_at DESC")).mappings().all()
    except Exception as e:
        st.error("Failed reading quotations.")
        st.exception(e)
        rows = []

    if rows:
        df = pd.DataFrame(rows)
        df['created_at'] = df['created_at'].apply(lambda x: x.strftime("%d %b %Y %H:%M") if x else "")
        st.dataframe(df[['quotation_number','customer_name','created_at','total']].rename(columns={
            'quotation_number':'Quotation No','customer_name':'Customer','created_at':'Date','total':'Total (₹)'
        }), use_container_width=True)

        selected = st.selectbox("Select Quotation", df['quotation_number'].tolist())
        if selected:
            row = df[df['quotation_number'] == selected].iloc[0]
            try:
                items = [(i[0], float(i[1]), float(i[2])) for i in ast.literal_eval(row["items"] or "[]")]
            except Exception:
                items = []
                st.error("Error parsing items from DB.")
            pdf_bytes = generate_pdf_bytes({
                "doc_number": row["quotation_number"], "company_name": row.get("company_name", "Data Center"),
                "company_address": row.get("company_address", ""), "customer_name": row.get("customer_name",""),
                "customer_address": row.get("customer_address",""), "cgst_rate": float(row.get("cgst_rate") or 0),
                "sgst_rate": float(row.get("sgst_rate") or 0), "discount": float(row.get("discount") or 0)
            }, items, doc_type="QUOTATION")

            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                st.download_button("⬇️ Download Quotation PDF", pdf_bytes, file_name=f"Quotation_{selected}.pdf", mime="application/pdf")
            with c2:
                confirm = st.checkbox("Confirm delete")
            with c3:
                if st.button("❌ Delete Quotation") and confirm:
                    delete_row("quotations", "quotation_number", selected)
                    st.success(f"Quotation {selected} deleted.")
    else:
        st.info("No quotations yet.")

# -----------------------
# Dashboard
# -----------------------
elif page == "Dashboard":
    st.subheader("Dashboard (Invoices + Quotations)")
    try:
        with engine.begin() as conn:
            total_invoices = conn.execute(text("SELECT COUNT(*) FROM invoices")).scalar() or 0
            total_quotations = conn.execute(text("SELECT COUNT(*) FROM quotations")).scalar() or 0
            total_rev_invoices = conn.execute(text("SELECT SUM(total) FROM invoices")).scalar() or 0
            total_rev_quotations = conn.execute(text("SELECT SUM(total) FROM quotations")).scalar() or 0
            combined_rev = (total_rev_invoices or 0) + (total_rev_quotations or 0)

            df_inv = pd.read_sql("SELECT invoice_number as doc_no, customer_name, total, created_at, 'Invoice' as type FROM invoices", conn) if total_invoices else pd.DataFrame()
            df_q = pd.read_sql("SELECT quotation_number as doc_no, customer_name, total, created_at, 'Quotation' as type FROM quotations", conn) if total_quotations else pd.DataFrame()
            df = pd.concat([df_inv, df_q], ignore_index=True) if not df_inv.empty or not df_q.empty else pd.DataFrame()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Invoices", total_invoices)
        c2.metric("Total Quotations", total_quotations)
        c3.metric("Combined Revenue (₹)", f"{combined_rev:,.2f}")

        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['date'] = df['created_at'].dt.date
            import plotly.express as px
            revenue_over_time = df.groupby('date')['total'].sum().reset_index()
            fig = px.line(revenue_over_time, x='date', y='total', title="Daily Combined Revenue", markers=True)
            st.plotly_chart(fig, use_container_width=True)

            top_customers = df.groupby('customer_name')['total'].sum().nlargest(10).reset_index()
            fig2 = px.bar(top_customers, x='customer_name', y='total', title="Top Customers (Combined)", text_auto='.2s')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No invoice/quotation data yet.")
    except Exception as e:
        st.error("Dashboard load failed.")
        st.exception(e)
