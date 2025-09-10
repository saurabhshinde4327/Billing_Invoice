# app.py
import os
import ast
import pandas as pd
import streamlit as st
from hashlib import sha256
from sqlalchemy import text

from db import engine, init_db, delete_row
from utils import parse_items
from pdf_gen import generate_professional_pdf as generate_pdf_bytes
from streamlit_autorefresh import st_autorefresh

# -----------------------
# Login Credentials
# -----------------------
DEFAULT_USER = "admin"
DEFAULT_PASS = "YcData@2027"

def hash_password(password):
    return sha256(password.encode()).hexdigest()

hashed_password = hash_password(DEFAULT_PASS)

# -----------------------
# Session Management
# -----------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def login():
    st.title("🔒 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == DEFAULT_USER and hash_password(password) == hashed_password:
            st.session_state['logged_in'] = True
            st.success("Logged in successfully!")
        else:
            st.error("Invalid username or password")

def logout():
    st.session_state['logged_in'] = False
    st.experimental_rerun()

# -----------------------
# Main App
# -----------------------
def main_app():
    st.set_page_config(page_title="Invoice & Quotation System", layout="wide", page_icon="🧾")
    
    # Sidebar Logout
    st.sidebar.write(f"Logged in as: **{DEFAULT_USER}**")
    if st.sidebar.button("Logout"):
        logout()

    st.title("Invoice & Quotation System")
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

                col_download, col_confirm, col_delete = st.columns(3)
                with col_download:
                    st.download_button("⬇️ Download PDF", pdf_bytes, file_name=f"Invoice_{selected}.pdf", mime="application/pdf")
                with col_confirm:
                    confirm = st.checkbox("Confirm delete")
                with col_delete:
                    if st.button("❌ Delete Invoice") and confirm:
                        delete_row("invoices", "invoice_number", selected)
                        st.success(f"Invoice {selected} deleted.")
        else:
            st.info("No invoices yet.")

    # -----------------------
    # Remaining pages (Quotations + Dashboard)...
    # -----------------------
    # You can replicate the same column fix for Quotation History, Dashboard etc.
    # Replace all usages of c1, c2, c3 with descriptive col_download, col_confirm, col_delete

# -----------------------
# Run the app
# -----------------------
if not st.session_state['logged_in']:
    login()
else:
    main_app()

