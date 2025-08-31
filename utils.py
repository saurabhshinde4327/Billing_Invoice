import os
from io import BytesIO
from PIL import Image
import streamlit as st
from sqlalchemy import text
from num2words import num2words
from reportlab.platypus import Image as RLImage
from db import engine

LOGO_PATH = "Logo.jpg"
GST_NO = "27AAATT1566E1ZJ"

def parse_items(items_text: str):
    items = []
    for line in items_text.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            st.error("Each item line must be: description | qty | price")
            st.stop()
        desc = "|".join(parts[:-2])
        qty = float(parts[-2])
        price = float(parts[-1])
        items.append((desc, qty, price))
    return items

def amount_in_words_international(amount):
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    words_rupees = num2words(rupees, lang='en').replace("-", " ").capitalize()
    result = f"{words_rupees} Rupees"
    if paise:
        words_paise = num2words(paise, lang='en').replace("-", " ")
        result += f", {words_paise} Paise"
    result += " only"
    return result

def delete_row(table: str, field: str, value: str):
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {table} WHERE {field} = :v"), {"v": value})

def make_logo_rlimage(max_width_px=80):
    if not os.path.exists(LOGO_PATH):
        return None
    try:
        with Image.open(LOGO_PATH) as im:
            if im.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", im.size, (255,255,255))
                bg.paste(im, mask=im.split()[3])
                im = bg
            w, h = im.size
            ratio = max_width_px / float(w)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            im_resized = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
            bio = BytesIO()
            im_resized.save(bio, format="PNG")
            bio.seek(0)
            return RLImage(bio, width=new_w, height=new_h)
    except Exception:
        return None
