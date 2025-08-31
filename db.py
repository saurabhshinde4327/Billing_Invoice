# db.py
import os
from sqlalchemy import create_engine, text

# -----------------------
# DB Config (set via ENV or defaults)
# -----------------------
DB_USER = os.getenv("DB_USER", "test")
DB_PASS = os.getenv("DB_PASS", "test123")
DB_HOST = os.getenv("DB_HOST", "91.108.105.168")
DB_NAME = os.getenv("DB_NAME", "invoice")

# Create SQLAlchemy engine (MySQL)
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}",
    pool_pre_ping=True
)

# -----------------------
# Initialize DB tables
# -----------------------
def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_number VARCHAR(64) UNIQUE,
                customer_name VARCHAR(255),
                customer_address TEXT,
                items TEXT,
                subtotal DECIMAL(12,2),
                cgst_rate DECIMAL(6,2),
                sgst_rate DECIMAL(6,2),
                discount DECIMAL(12,2),
                total DECIMAL(12,2),
                company_name VARCHAR(255),
                company_address TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS quotations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                quotation_number VARCHAR(64) UNIQUE,
                customer_name VARCHAR(255),
                customer_address TEXT,
                items TEXT,
                subtotal DECIMAL(12,2),
                cgst_rate DECIMAL(6,2),
                sgst_rate DECIMAL(6,2),
                discount DECIMAL(12,2),
                total DECIMAL(12,2),
                company_name VARCHAR(255),
                company_address TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

# -----------------------
# Delete row helper
# -----------------------
def delete_row(table: str, field: str, value: str):
    """Delete a row from given table where field = value"""
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {table} WHERE {field} = :v"), {"v": value})
