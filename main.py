import streamlit as st
from PIL import Image, ImageStat, ImageFilter
import numpy as np
import sqlite3
import io
import datetime
import base64
import os

# -------------------------
# Database helpers
# -------------------------
DB_PATH = "market.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            quantity TEXT,
            base_price REAL,
            image BLOB,
            grade TEXT,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            bidder_name TEXT,
            bid_amount REAL,
            bid_time TEXT,
            FOREIGN KEY(listing_id) REFERENCES listings(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            buyer_name TEXT,
            amount REAL,
            status TEXT,
            timestamp TEXT,
            note TEXT,
            FOREIGN KEY(listing_id) REFERENCES listings(id)
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

# -------------------------
# Utilities
# -------------------------
def pil_image_to_bytes(img: Image.Image):
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def bytes_to_pil_image(b: bytes):
    return Image.open(io.BytesIO(b))

def now_str():
    return datetime.datetime.utcnow().isoformat() + "Z"

# -------------------------
# Simple image "AI" grader
# (placeholder — replace with a real model if desired)
# Criteria used:
#  - brightness (avg channel)
#  - sharpness (via edge enhancement / laplacian-ish by using filter and variance)
# -------------------------
def grade_image(pil_img: Image.Image):
    # convert to RGB, resize to speed up calc
    img = pil_img.convert("RGB").resize((300,300))
    stat = ImageStat.Stat(img)
    # brightness as average of channels
    brightness = sum(stat.mean) / 3.0  # 0-255
    # measure "sharpness" via variance of grayscale
    gray = img.convert("L")
    arr = np.asarray(gray).astype(np.float32)
    var = arr.var()
    # simple scoring
    score = (brightness / 255.0) * 0.6 + (min(var / 2000.0, 1.0)) * 0.4
    # Map score to grade
    if score > 0.68:
        return "A"
    elif score > 0.45:
        return "B"
    else:
        return "C"

# -------------------------
# CRUD + business logic
# -------------------------
def create_listing(title, description, quantity, base_price, image_bytes, grade):
    c = conn.cursor()
    c.execute('''
        INSERT INTO listings (title, description, quantity, base_price, image, grade, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (title, description, quantity, base_price, image_bytes, grade, now_str()))
    conn.commit()
    return c.lastrowid

def get_listings():
    c = conn.cursor()
    c.execute('SELECT id, title, description, quantity, base_price, image, grade, created_at FROM listings ORDER BY created_at DESC')
    return c.fetchall()

def get_listing(listing_id):
    c = conn.cursor()
    c.execute('SELECT id, title, description, quantity, base_price, image, grade, created_at FROM listings WHERE id=?', (listing_id,))
    return c.fetchone()

def get_highest_bid(listing_id):
    c = conn.cursor()
    c.execute('SELECT bidder_name, bid_amount, bid_time FROM bids WHERE listing_id=? ORDER BY bid_amount DESC, bid_time ASC LIMIT 1', (listing_id,))
    return c.fetchone()

def add_bid(listing_id, bidder_name, amount):
    c = conn.cursor()
    c.execute('INSERT INTO bids (listing_id, bidder_name, bid_amount, bid_time) VALUES (?, ?, ?, ?)',
              (listing_id, bidder_name, amount, now_str()))
    conn.commit()
    return c.lastrowid

def record_transaction(listing_id, buyer_name, amount, status="Completed", note="Simulated payment"):
    c = conn.cursor()
    c.execute('INSERT INTO transactions (listing_id, buyer_name, amount, status, timestamp, note) VALUES (?, ?, ?, ?, ?, ?)',
              (listing_id, buyer_name, amount, status, now_str(), note))
    conn.commit()
    return c.lastrowid

def get_transactions():
    c = conn.cursor()
    c.execute('SELECT id, listing_id, buyer_name, amount, status, timestamp, note FROM transactions ORDER BY timestamp DESC')
    return c.fetchall()

def get_bids_for_listing(listing_id):
    c = conn.cursor()
    c.execute('SELECT bidder_name, bid_amount, bid_time FROM bids WHERE listing_id=? ORDER BY bid_amount DESC', (listing_id,))
    return c.fetchall()

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="AgriMarket", page_icon="🌾", layout="wide")

st.title("🌾 AgriMarket — Digital Marketplace for Farmers")

menu = st.sidebar.selectbox("Choose a page", ["Create Listing", "Browse & Bid", "Transactions / Admin", "How to integrate real AI & Payments"])

if menu == "Create Listing":
    st.header("Create a new produce listing")
    with st.form("create_form", clear_on_submit=True):
        title = st.text_input("Produce name (e.g., 'Tomatoes - Fresh')", max_chars=120)
        description = st.text_area("Description (variety, harvest date, storage, etc.)", height=120)
        quantity = st.text_input("Quantity (e.g., '100 kg' or '50 crates')")
        base_price = st.number_input("Base price (₹ per unit or per kg)", min_value=0.0, format="%.2f")
        image_file = st.file_uploader("Upload an image (optional) — can be used for quality grading", type=["png","jpg","jpeg"])
        do_grade = st.checkbox("Run automatic quality grading on image (simple heuristic)", value=True)
        submitted = st.form_submit_button("Create listing")

    if submitted:
        if not title:
            st.error("Please provide a produce name.")
        else:
            image_bytes = None
            grade = None
            if image_file is not None:
                img = Image.open(image_file)
                image_bytes = pil_image_to_bytes(img)
                if do_grade:
                    try:
                        grade = grade_image(img)
                    except Exception as e:
                        st.warning(f"Grading failed: {e}")
                        grade = None
            listing_id = create_listing(title, description, quantity, base_price, image_bytes, grade)
            st.success(f"Listing created (ID: {listing_id})")
            if grade:
                st.info(f"Assigned grade: {grade}")

elif menu == "Browse & Bid":
    st.header("Browse listings and place bids")
    listings = get_listings()
    if not listings:
        st.info("No listings yet. Ask a farmer to add produce.")
    else:
        for row in listings:
            (lid, title, description, quantity, base_price, image_blob, grade, created_at) = row
            card = st.container()
            with card:
                cols = st.columns([1,3])
                with cols[0]:
                    if image_blob:
                        img = bytes_to_pil_image(image_blob)
                        st.image(img, use_column_width=True, caption=f"Grade: {grade}" if grade else "No grade")
                    else:
                        st.write("No image")
                with cols[1]:
                    st.subheader(f"{title}  —  {quantity}")
                    st.write(description)
                    st.write(f"Base price: ₹{base_price:.2f}")
                    if grade:
                        st.write(f"Quality grade: **{grade}**")
                    st.write(f"Listing created: {created_at.split('T')[0]}")
                    hb = get_highest_bid(lid)
                    if hb:
                        st.write(f"Highest bid: ₹{hb[1]:.2f} by {hb[0]} at {hb[2]}")
                    else:
                        st.write("No bids yet")
                    # show all bids
                    with st.expander("See all bids"):
                        bids = get_bids_for_listing(lid)
                        if not bids:
                            st.write("No bids")
                        else:
                            for b in bids:
                                st.write(f"₹{b[1]:.2f} — {b[0]} at {b[2]}")
                    # bidding form
                    with st.form(f"bid_form_{lid}", clear_on_submit=False):
                        bidder_name = st.text_input("Your name", key=f"name_{lid}")
                        current_offer = float(hb[1]) if hb else base_price
                        bid_amount = st.number_input(f"Your bid (must be greater than ₹{current_offer:.2f})", min_value=0.0, format="%.2f", key=f"bid_{lid}")
                        place = st.form_submit_button("Place bid")
                        if place:
                            if not bidder_name:
                                st.error("Enter your name to place a bid.")
                            elif bid_amount <= current_offer:
                                st.error(f"Your bid must be greater than current highest ₹{current_offer:.2f}")
                            else:
                                add_bid(lid, bidder_name, bid_amount)
                                st.success(f"Bid of ₹{bid_amount:.2f} placed by {bidder_name}")
                                st.experimental_rerun()  # refresh to show updated highest bid

                    # Simulated buy/pay now block
                    st.markdown("---")
                    st.write("If you have the highest bid and want to complete the purchase, use the payment area below.")
                    with st.form(f"pay_form_{lid}"):
                        pay_buyer = st.text_input("Buyer name (to record transaction)", key=f"payname_{lid}")
                        pay_amount = st.number_input("Pay amount (₹)", min_value=0.0, format="%.2f", key=f"payamount_{lid}")
                        pay_note = st.text_input("Note (optional)", key=f"paynote_{lid}")
                        pay = st.form_submit_button("Simulate Pay & Record Transaction")
                        if pay:
                            # In a real system you'd check order ownership, payment gateway confirmation, etc.
                            if not pay_buyer:
                                st.error("Provide buyer name.")
                            elif pay_amount <= 0.0:
                                st.error("Pay amount must be positive.")
                            else:
                                # Simulate payment processing
                                # TODO: integrate with Stripe/PayPal here and only record on successful confirmation
                                tid = record_transaction(lid, pay_buyer, pay_amount, status="Completed", note=pay_note or "Simulated payment")
                                st.success(f"Payment recorded (Transaction ID: {tid}).")
                                st.info("This is a simulated payment. Replace with a real gateway for production.")

elif menu == "Transactions / Admin":
    st.header("Transactions and admin controls")
    st.subheader("All transactions")
    txs = get_transactions()
    if not txs:
        st.info("No transactions yet.")
    else:
        for tx in txs:
            tid, lid, buyer, amount, status, ts, note = tx
            st.write(f"Txn {tid} | Listing {lid} | Buyer: {buyer} | ₹{amount:.2f} | Status: {status} | Time: {ts}")
            if note:
                st.write(f"> {note}")
            st.markdown("---")

    st.subheader("All listings (admin view)")
    listings = get_listings()
    for row in listings:
        lid, title, description, quantity, base_price, image_blob, grade, created_at = row
        cols = st.columns([1,4])
        with cols[0]:
            if image_blob:
                st.image(bytes_to_pil_image(image_blob), use_column_width=True)
            else:
                st.write("No image")
        with cols[1]:
            st.write(f"ID: {lid} | {title} | Qty: {quantity} | Base: ₹{base_price:.2f} | Grade: {grade}")
            st.write(description)
            if st.button(f"Delete listing {lid}", key=f"del_{lid}"):
                # simple admin delete
                c = conn.cursor()
                c.execute('DELETE FROM listings WHERE id=?', (lid,))
                c.execute('DELETE FROM bids WHERE listing_id=?', (lid,))
                c.execute('DELETE FROM transactions WHERE listing_id=?', (lid,))
                conn.commit()
                st.success(f"Deleted listing {lid} and related bids/transactions.")
                st.experimental_rerun()

elif menu == "How to integrate real AI & Payments":
    st.header("Guidance: replace simulated grading & payments with production components")
    st.markdown("""
    **Image-based quality grading (replace placeholder):**
    - Train or fine-tune a model to grade produce (e.g., TensorFlow/Keras or PyTorch). Typical approaches:
      - Classification model (A/B/C) using labelled images.
      - Use transfer learning (MobileNet / EfficientNet) for small datasets.
      - Add metadata (size, color histogram, defects detected) to improve grading.
    - For inference in this Streamlit app:
      - Export a lightweight model (ONNX/TFLite) and run inference on the uploaded image.
      - Or provide an API endpoint (FastAPI) that the app calls to grade images.

    **Digital payments (production-ready):**
    - Use a payment gateway: Stripe / PayPal / Razorpay (India).
    - Typical flow:
      1. Create an order on your backend (FastAPI/Flask/Django), store order details.
      2. Create a PaymentIntent (Stripe) or order (Razorpay) and pass client token to the frontend.
      3. Confirm payment on the frontend and verify webhook on the backend.
      4. Only after webhook confirmation, record transaction as 'Completed' in DB.
    - Keep secret keys on server side only.

    **Security & Scalability notes**
    - Move DB to a proper DB server (Postgres / MySQL).
    - Protect endpoints with authentication (farmers vs buyers vs admin).
    - Validate uploaded images (size/format), scan for malware, limit file size.
    - Add rate-limiting and monitoring.

    If you want, I can:
    - turn the grading placeholder into a small TF/PyTorch demo,
    - add a FastAPI backend and show an example Stripe integration,
    - or wire this app to a remote Postgres DB and Dockerize it.
    """)
