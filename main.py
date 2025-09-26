import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import uuid
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import io
import base64
import random
import numpy as np

# Set page configuration
st.set_page_config(
    page_title="AgriMarket Pro",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #2E7D32, #4CAF50);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .produce-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #4CAF50;
    }
    
    .grade-premium { background-color: #28a745; color: white; padding: 0.25rem 0.5rem; border-radius: 15px; }
    .grade-a { background-color: #17a2b8; color: white; padding: 0.25rem 0.5rem; border-radius: 15px; }
    .grade-b { background-color: #ffc107; color: black; padding: 0.25rem 0.5rem; border-radius: 15px; }
    .grade-c { background-color: #dc3545; color: white; padding: 0.25rem 0.5rem; border-radius: 15px; }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    
    .bid-success { background-color: #d4edda; padding: 1rem; border-radius: 5px; border: 1px solid #c3e6cb; }
    .bid-pending { background-color: #fff3cd; padding: 1rem; border-radius: 5px; border: 1px solid #ffeaa7; }
    .bid-rejected { background-color: #f8d7da; padding: 1rem; border-radius: 5px; border: 1px solid #f5c6cb; }
</style>
""", unsafe_allow_html=True)

# Database initialization
@st.cache_resource
def init_database():
    conn = sqlite3.connect('agri_marketplace.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            user_type TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Produce table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produce (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            base_price REAL NOT NULL,
            quality_grade TEXT,
            harvest_date DATE,
            expiry_date DATE,
            location TEXT,
            image_data TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (farmer_id) REFERENCES users (id)
        )
    ''')
    
    # Bids table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produce_id INTEGER NOT NULL,
            buyer_id INTEGER NOT NULL,
            bid_amount REAL NOT NULL,
            quantity_requested REAL NOT NULL,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produce_id) REFERENCES produce (id),
            FOREIGN KEY (buyer_id) REFERENCES users (id)
        )
    ''')
    
    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            bid_id INTEGER NOT NULL,
            farmer_id INTEGER NOT NULL,
            buyer_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT,
            payment_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bid_id) REFERENCES bids (id),
            FOREIGN KEY (farmer_id) REFERENCES users (id),
            FOREIGN KEY (buyer_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    return conn

# AI Quality Analysis Simulation
def analyze_produce_quality(image):
    """
    Simulate AI-based quality analysis of produce images
    In production, this would integrate with actual computer vision models
    """
    if image is not None:
        # Simulate analysis based on image properties
        img_array = np.array(image)
        
        # Simulate quality metrics
        brightness = np.mean(img_array)
        color_variance = np.var(img_array)
        
        # Generate quality grade based on simulated analysis
        if brightness > 120 and color_variance > 1000:
            grade = "Premium"
            confidence = random.uniform(90, 98)
            defects = "None detected"
            freshness = random.uniform(95, 100)
        elif brightness > 100:
            grade = "A"
            confidence = random.uniform(80, 90)
            defects = random.choice(["None", "Minor discoloration"])
            freshness = random.uniform(85, 95)
        elif brightness > 80:
            grade = "B"
            confidence = random.uniform(70, 80)
            defects = random.choice(["Minor spots", "Small bruises"])
            freshness = random.uniform(75, 85)
        else:
            grade = "C"
            confidence = random.uniform(60, 70)
            defects = random.choice(["Visible damage", "Color variations"])
            freshness = random.uniform(60, 75)
    else:
        grade = "Not Graded"
        confidence = 0
        defects = "No image provided"
        freshness = 0
    
    return {
        'grade': grade,
        'confidence': confidence,
        'defects': defects,
        'freshness_score': freshness
    }

# Utility functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hash_password):
    return hash_password == hashlib.sha256(password.encode()).hexdigest()

def generate_transaction_id():
    return f"TXN_{uuid.uuid4().hex[:8].upper()}"

# Session state initialization
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'username' not in st.session_state:
    st.session_state.username = None

# Initialize database
conn = init_database()

def main():
    st.markdown("""
    <div class="main-header">
        <h1>🌾 AgriMarket Pro</h1>
        <p>AI-Powered Agricultural Marketplace with Smart Bidding & Secure Payments</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    if st.session_state.authenticated:
        st.sidebar.success(f"Welcome, {st.session_state.username}!")
        st.sidebar.write(f"Role: {st.session_state.user_type.title()}")
        
        if st.session_state.user_type == 'farmer':
            page = st.sidebar.selectbox("Navigate", [
                "🏠 Dashboard", 
                "📦 My Produce", 
                "➕ Add Produce", 
                "💰 Bids & Transactions",
                "📊 Analytics"
            ])
        else:  # buyer
            page = st.sidebar.selectbox("Navigate", [
                "🏠 Dashboard", 
                "🛒 Browse Produce", 
                "💰 My Bids", 
                "💳 Transactions",
                "📈 Market Trends"
            ])
        
        if st.sidebar.button("🚪 Logout"):
            for key in ['authenticated', 'user_id', 'user_type', 'username']:
                st.session_state[key] = None if key != 'authenticated' else False
            st.rerun()
    else:
        page = st.sidebar.selectbox("Choose Action", ["🔑 Login", "📝 Register", "🌾 Browse (Guest)"])
    
    # Page routing
    if not st.session_state.authenticated:
        if page == "🔑 Login":
            login_page()
        elif page == "📝 Register":
            register_page()
        elif page == "🌾 Browse (Guest)":
            browse_produce_page(guest_mode=True)
    else:
        if page == "🏠 Dashboard":
            dashboard_page()
        elif page == "📦 My Produce":
            my_produce_page()
        elif page == "➕ Add Produce":
            add_produce_page()
        elif page == "💰 Bids & Transactions" or page == "💳 Transactions":
            transactions_page()
        elif page == "🛒 Browse Produce":
            browse_produce_page()
        elif page == "💰 My Bids":
            my_bids_page()
        elif page == "📊 Analytics" or page == "📈 Market Trends":
            analytics_page()

def login_page():
    st.header("🔑 Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            email = st.text_input("📧 Email")
            password = st.text_input("🔒 Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, user_type, password_hash FROM users WHERE email = ?", (email,))
                user = cursor.fetchone()
                
                if user and verify_password(password, user[3]):
                    st.session_state.authenticated = True
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.session_state.user_type = user[2]
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid email or password")

def register_page():
    st.header("📝 Register")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("register_form"):
            username = st.text_input("👤 Username")
            email = st.text_input("📧 Email")
            password = st.text_input("🔒 Password", type="password")
            confirm_password = st.text_input("🔒 Confirm Password", type="password")
            user_type = st.selectbox("👥 User Type", ["farmer", "buyer"])
            phone = st.text_input("📱 Phone (Optional)")
            address = st.text_area("📍 Address (Optional)")
            
            submit = st.form_submit_button("Register", use_container_width=True)
            
            if submit:
                if password != confirm_password:
                    st.error("Passwords don't match!")
                    return
                
                cursor = conn.cursor()
                
                # Check if user already exists
                cursor.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username))
                if cursor.fetchone():
                    st.error("User with this email or username already exists!")
                    return
                
                # Create new user
                try:
                    cursor.execute("""
                        INSERT INTO users (username, email, password_hash, user_type, phone, address)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (username, email, hash_password(password), user_type, phone, address))
                    conn.commit()
                    st.success("Registration successful! Please login.")
                except Exception as e:
                    st.error(f"Registration failed: {str(e)}")

def dashboard_page():
    st.header("🏠 Dashboard")
    
    if st.session_state.user_type == 'farmer':
        farmer_dashboard()
    else:
        buyer_dashboard()

def farmer_dashboard():
    cursor = conn.cursor()
    
    # Fetch farmer statistics
    cursor.execute("SELECT COUNT(*) FROM produce WHERE farmer_id = ?", (st.session_state.user_id,))
    total_listings = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM produce WHERE farmer_id = ? AND status = 'active'", (st.session_state.user_id,))
    active_listings = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM bids b 
        JOIN produce p ON b.produce_id = p.id 
        WHERE p.farmer_id = ? AND b.status = 'pending'
    """, (st.session_state.user_id,))
    pending_bids = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COALESCE(SUM(t.amount), 0) FROM transactions t 
        WHERE t.farmer_id = ? AND t.payment_status = 'completed'
    """, (st.session_state.user_id,))
    total_earnings = cursor.fetchone()[0]
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>📦</h3>
            <h2>{}</h2>
            <p>Total Listings</p>
        </div>
        """.format(total_listings), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>✅</h3>
            <h2>{}</h2>
            <p>Active Listings</p>
        </div>
        """.format(active_listings), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>⏳</h3>
            <h2>{}</h2>
            <p>Pending Bids</p>
        </div>
        """.format(pending_bids), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3>💰</h3>
            <h2>${:.2f}</h2>
            <p>Total Earnings</p>
        </div>
        """.format(total_earnings), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent bids
    st.subheader("🎯 Recent Bids")
    cursor.execute("""
        SELECT b.*, p.title, u.username, b.created_at
        FROM bids b
        JOIN produce p ON b.produce_id = p.id
        JOIN users u ON b.buyer_id = u.id
        WHERE p.farmer_id = ?
        ORDER BY b.created_at DESC
        LIMIT 10
    """, (st.session_state.user_id,))
    
    recent_bids = cursor.fetchall()
    
    if recent_bids:
        for bid in recent_bids:
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**{bid[5]}** by {bid[6]}")
                st.write(f"Quantity: {bid[4]} units")
            
            with col2:
                st.write(f"Bid: ${bid[3]:.2f}")
                st.write(f"Total: ${bid[3] * bid[4]:.2f}")
            
            with col3:
                status_class = f"bid-{bid[6]}" if bid[6] in ['success', 'pending', 'rejected'] else 'bid-pending'
                st.markdown(f'<div class="{status_class}">{bid[6].title()}</div>', unsafe_allow_html=True)
                
                if bid[6] == 'pending':
                    if st.button(f"Accept", key=f"accept_{bid[0]}"):
                        accept_bid(bid[0])
                    if st.button(f"Reject", key=f"reject_{bid[0]}"):
                        reject_bid(bid[0])
            
            st.markdown("---")
    else:
        st.info("No bids yet. Add more produce to attract buyers!")

def buyer_dashboard():
    cursor = conn.cursor()
    
    # Fetch buyer statistics
    cursor.execute("SELECT COUNT(*) FROM bids WHERE buyer_id = ?", (st.session_state.user_id,))
    total_bids = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bids WHERE buyer_id = ? AND status = 'pending'", (st.session_state.user_id,))
    pending_bids = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bids WHERE buyer_id = ? AND status = 'accepted'", (st.session_state.user_id,))
    accepted_bids = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COALESCE(SUM(t.amount), 0) FROM transactions t 
        WHERE t.buyer_id = ? AND t.payment_status = 'completed'
    """, (st.session_state.user_id,))
    total_spent = cursor.fetchone()[0]
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🎯</h3>
            <h2>{}</h2>
            <p>Total Bids</p>
        </div>
        """.format(total_bids), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>⏳</h3>
            <h2>{}</h2>
            <p>Pending Bids</p>
        </div>
        """.format(pending_bids), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>✅</h3>
            <h2>{}</h2>
            <p>Accepted Bids</p>
        </div>
        """.format(accepted_bids), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3>💳</h3>
            <h2>${:.2f}</h2>
            <p>Total Spent</p>
        </div>
        """.format(total_spent), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent produce
    st.subheader("🌾 Fresh Produce")
    cursor.execute("""
        SELECT p.*, u.username as farmer_name
        FROM produce p
        JOIN users u ON p.farmer_id = u.id
        WHERE p.status = 'active'
        ORDER BY p.created_at DESC
        LIMIT 6
    """)
    
    recent_produce = cursor.fetchall()
    
    if recent_produce:
        cols = st.columns(3)
        for idx, produce in enumerate(recent_produce):
            with cols[idx % 3]:
                display_produce_card(produce)
    else:
        st.info("No produce available at the moment.")

def add_produce_page():
    st.header("➕ Add New Produce")
    
    with st.form("add_produce_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("🏷️ Product Title *")
            category = st.selectbox("🗂️ Category *", [
                "Vegetables", "Fruits", "Grains", "Pulses", 
                "Spices", "Herbs", "Dairy", "Others"
            ])
            quantity = st.number_input("📊 Quantity *", min_value=0.1, step=0.1)
            unit = st.selectbox("📏 Unit *", ["kg", "tons", "bags", "boxes", "pieces"])
            base_price = st.number_input("💰 Base Price (per unit) *", min_value=0.01, step=0.01)
        
        with col2:
            harvest_date = st.date_input("📅 Harvest Date", max_value=date.today())
            expiry_date = st.date_input("⏰ Expiry Date", min_value=date.today())
            location = st.text_input("📍 Location *")
            
            # Image upload
            uploaded_image = st.file_uploader(
                "📸 Upload Product Image", 
                type=['png', 'jpg', 'jpeg'],
                help="Upload a clear image for AI quality analysis"
            )
        
        description = st.text_area("📝 Description")
        
        submit = st.form_submit_button("🚀 Add Produce", use_container_width=True)
        
        if submit:
            if not all([title, category, quantity, unit, base_price, location]):
                st.error("Please fill in all required fields marked with *")
                return
            
            # Process image and get AI analysis
            image_data = None
            quality_grade = "Not Graded"
            
            if uploaded_image:
                # Convert image to base64 for storage
                image = Image.open(uploaded_image)
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                image_data = base64.b64encode(buffer.getvalue()).decode()
                
                # AI quality analysis
                analysis = analyze_produce_quality(image)
                quality_grade = analysis['grade']
                
                # Display analysis results
                st.success("🤖 AI Quality Analysis Complete!")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Quality Grade", analysis['grade'])
                with col2:
                    st.metric("Confidence", f"{analysis['confidence']:.1f}%")
                with col3:
                    st.metric("Freshness Score", f"{analysis['freshness_score']:.1f}")
                
                st.info(f"Defects: {analysis['defects']}")
            
            # Insert into database
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO produce (
                        farmer_id, title, description, category, quantity, unit, 
                        base_price, quality_grade, harvest_date, expiry_date, 
                        location, image_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    st.session_state.user_id, title, description, category, 
                    quantity, unit, base_price, quality_grade, harvest_date, 
                    expiry_date, location, image_data
                ))
                conn.commit()
                st.success("✅ Produce added successfully!")
                
                # Clear form by rerunning
                st.balloons()
                
            except Exception as e:
                st.error(f"Error adding produce: {str(e)}")

def browse_produce_page(guest_mode=False):
    st.header("🛒 Browse Fresh Produce")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        category_filter = st.selectbox("Category", ["All"] + [
            "Vegetables", "Fruits", "Grains", "Pulses", 
            "Spices", "Herbs", "Dairy", "Others"
        ])
    
    with col2:
        quality_filter = st.selectbox("Quality Grade", ["All", "Premium", "A", "B", "C"])
    
    with col3:
        location_filter = st.text_input("Location")
    
    with col4:
        sort_by = st.selectbox("Sort By", ["Newest", "Price Low-High", "Price High-Low", "Quality"])
    
    # Build query
    query = """
        SELECT p.*, u.username as farmer_name
        FROM produce p
        JOIN users u ON p.farmer_id = u.id
        WHERE p.status = 'active'
    """
    params = []
    
    if category_filter != "All":
        query += " AND p.category = ?"
        params.append(category_filter)
    
    if quality_filter != "All":
        query += " AND p.quality_grade = ?"
        params.append(quality_filter)
    
    if location_filter:
        query += " AND p.location LIKE ?"
        params.append(f"%{location_filter}%")
    
    # Add sorting
    if sort_by == "Newest":
        query += " ORDER BY p.created_at DESC"
    elif sort_by == "Price Low-High":
        query += " ORDER BY p.base_price ASC"
    elif sort_by == "Price High-Low":
        query += " ORDER BY p.base_price DESC"
    elif sort_by == "Quality":
        query += " ORDER BY p.quality_grade ASC"
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    produce_list = cursor.fetchall()
    
    if produce_list:
        # Display produce in cards
        cols = st.columns(3)
        for idx, produce in enumerate(produce_list):
            with cols[idx % 3]:
                display_produce_card(produce, guest_mode)
    else:
        st.info("No produce found matching your criteria.")

def display_produce_card(produce, guest_mode=False):
    """Display a produce card with bidding functionality"""
    
    # Unpack produce data
    (id, farmer_id, title, description, category, quantity, unit, base_price, 
     quality_grade, harvest_date, expiry_date, location, image_data, 
     status, created_at, farmer_name) = produce
    
    with st.container():
        st.markdown('<div class="produce-card">', unsafe_allow_html=True)
        
        # Display image if available
        if image_data:
            try:
                image = Image.open(io.BytesIO(base64.b64decode(image_data)))
                st.image(image, use_column_width=True)
            except:
                st.image("https://via.placeholder.com/300x200/28a745/ffffff?text=Produce", use_column_width=True)
        else:
            st.image("https://via.placeholder.com/300x200/28a745/ffffff?text=Produce", use_column_width=True)
        
        st.subheader(title)
        
        # Quality badge
        grade_class = f"grade-{quality_grade.lower()}" if quality_grade != "Not Graded" else "grade-c"
        st.markdown(f'<span class="{grade_class}">Grade {quality_grade}</span>', unsafe_allow_html=True)
        
        st.write(f"**Category:** {category}")
        st.write(f"**Quantity:** {quantity} {unit}")
        st.write(f"**Price:** ${base_price:.2f} per {unit}")
        st.write(f"**Location:** {location}")
        st.write(f"**Farmer:** {farmer_name}")
        
        if description:
            st.write(f"**Description:** {description}")
        
        # Bidding section (only for authenticated buyers)
        if not guest_mode and st.session_state.authenticated and st.session_state.user_type == 'buyer':
            st.markdown("---")
            st.write("**Place Your Bid:**")
            
            with st.form(f"bid_form_{id}"):
                bid_amount = st.number_input(f"Bid Amount (per {unit})", min_value=0.01, step=0.01, key=f"bid_amount_{id}")
                quantity_requested = st.number_input(f"Quantity ({unit})", min_value=0.1, max_value=quantity, step=0.1, key=f"quantity_{id}")
                message = st.text_area("Message (Optional)", key=f"message_{id}")
                
                if st.form_submit_button("Place Bid", use_container_width=True):
                    place_bid(id, bid_amount, quantity_requested, message)
        
        elif guest_mode:
            st.info("Login as a buyer to place bids")
        
        st.markdown('</div>', unsafe_allow_html=True)

def place_bid(produce_id, bid_amount, quantity_requested, message):
    """Place a bid on produce"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO bids (produce_id, buyer_id, bid_amount, quantity_requested, message)
            VALUES (?, ?, ?, ?, ?)
        """, (produce_id, st.session_state.user_id, bid_amount, quantity_requested, message))
        conn.commit()
        st.success("🎯 Bid placed successfully!")
        st.balloons()
    except Exception as e:
        st.error(f"Error placing bid: {str(e)}")

def accept_bid(bid_id):
    """Accept a bid and create transaction"""
    cursor = conn.cursor()
    try:
        # Get bid details
        cursor.execute("""
            SELECT b.*, p.title FROM bids b
            JOIN produce p ON b.produce_id = p.id
            WHERE b.id = ?
        """, (bid_id,))
        bid = cursor.fetchone()
        
        if bid:
            # Update bid status
            cursor.execute("UPDATE bids SET status = 'accepted' WHERE id = ?", (bid_id,))
            
            # Create transaction
            transaction_id = generate_transaction_id()
            total_amount = bid[3] * bid[4]  # bid_amount * quantity_requested
            
            cursor.execute("""
                INSERT INTO transactions (transaction_id, bid_id, farmer_id, buyer_id, amount)
                VALUES (?, ?, ?, ?, ?)
            """, (transaction_id, bid_id, st.session_state.user_id, bid[2], total_amount))
            
            conn.commit()
            st.success(f"✅ Bid accepted! Transaction ID: {transaction_id}")
            st.rerun()
    except Exception as e:
        st.error(f"Error accepting bid: {str(e)}")

def reject_bid(bid_id):
    """Reject a bid"""
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE bids SET status = 'rejected' WHERE id = ?", (bid_id,))
        conn.commit()
        st.success("❌ Bid rejected")
        st.rerun()
    except Exception as e:
        st.error(f"Error rejecting bid: {str(e)}")

def my_produce_page():
    st.header("📦 My Produce Listings")
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM produce 
        WHERE farmer_id = ?
        ORDER BY created_at DESC
    """, (st.session_state.user_id,))
    
    produce_list = cursor.fetchall()
    
    if produce_list:
        for produce in produce_list:
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.subheader(produce[2])  # title
                st.write(f"Category: {produce[4]}")
                st.write(f"Quantity: {produce[5]} {produce[6]}")
                st.write(f"Price: ${produce[7]:.2f} per {produce[6]}")
                
                grade_class = f"grade-{produce[8].lower()}" if produce[8] != "Not Graded" else "grade-c"
                st.markdown(f'<span class="{grade_class}">Grade {produce[8]}</span>', unsafe_allow_html=True)
            
            with col2:
                st.write(f"Location: {produce[11]}")
                st.write(f"Status: {produce[13].title()}")
                st.write(f"Listed: {produce[14][:10]}")
                
                # Get bid count
                cursor.execute("SELECT COUNT(*) FROM bids WHERE produce_id = ?", (produce[0],))
                bid_count = cursor.fetchone()[0]
                st.write(f"Bids received: {bid_count}")
            
            with col3:
                if st.button(f"View Bids", key=f"view_bids_{produce[0]}"):
                    view_produce_bids(produce[0])
                
                if produce[13] == 'active':
                    if st.button(f"Mark as Sold", key=f"sold_{produce[0]}"):
                        mark_as_sold(produce[0])
            
            st.markdown("---")
    else:
        st.info("No produce listed yet. Add your first listing!")

def view_produce_bids(produce_id):
    """Display bids for a specific produce item"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, u.username, p.title
        FROM bids b
        JOIN users u ON b.buyer_id = u.id
        JOIN produce p ON b.produce_id = p.id
        WHERE b.produce_id = ?
        ORDER BY b.created_at DESC
    """, (produce_id,))
    
    bids = cursor.fetchall()
    
    if bids:
        st.subheader(f"Bids for: {bids[0][7]}")
        
        for bid in bids:
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**Buyer:** {bid[6]}")
                st.write(f"**Quantity:** {bid[4]} units")
                st.write(f"**Message:** {bid[5] or 'No message'}")
            
            with col2:
                st.write(f"**Bid:** ${bid[3]:.2f} per unit")
                st.write(f"**Total:** ${bid[3] * bid[4]:.2f}")
                st.write(f"**Date:** {bid[7][:10]}")
            
            with col3:
                status_class = f"bid-{bid[6]}" if bid[6] in ['success', 'pending', 'rejected'] else 'bid-pending'
                st.markdown(f'<div class="{status_class}">{bid[6].title()}</div>', unsafe_allow_html=True)
                
                if bid[6] == 'pending':
                    if st.button(f"Accept", key=f"accept_bid_{bid[0]}"):
                        accept_bid(bid[0])
                    if st.button(f"Reject", key=f"reject_bid_{bid[0]}"):
                        reject_bid(bid[0])
            
            st.markdown("---")
    else:
        st.info("No bids received yet.")

def mark_as_sold(produce_id):
    """Mark produce as sold"""
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE produce SET status = 'sold' WHERE id = ?", (produce_id,))
        conn.commit()
        st.success("✅ Marked as sold!")
        st.rerun()
    except Exception as e:
        st.error(f"Error updating status: {str(e)}")

def my_bids_page():
    st.header("💰 My Bids")
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, p.title, p.unit, u.username as farmer_name
        FROM bids b
        JOIN produce p ON b.produce_id = p.id
        JOIN users u ON p.farmer_id = u.id
        WHERE b.buyer_id = ?
        ORDER BY b.created_at DESC
    """, (st.session_state.user_id,))
    
    bids = cursor.fetchall()
    
    if bids:
        for bid in bids:
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**Product:** {bid[7]}")
                st.write(f"**Farmer:** {bid[9]}")
                st.write(f"**Quantity:** {bid[4]} {bid[8]}")
            
            with col2:
                st.write(f"**Bid:** ${bid[3]:.2f} per {bid[8]}")
                st.write(f"**Total:** ${bid[3] * bid[4]:.2f}")
                st.write(f"**Date:** {bid[7][:10]}")
            
            with col3:
                status_class = f"bid-{bid[6]}" if bid[6] in ['accepted', 'pending', 'rejected'] else 'bid-pending'
                st.markdown(f'<div class="{status_class}">{bid[6].title()}</div>', unsafe_allow_html=True)
                
                if bid[6] == 'accepted':
                    # Check if payment is pending
                    cursor.execute("SELECT payment_status FROM transactions WHERE bid_id = ?", (bid[0],))
                    transaction = cursor.fetchone()
                    if transaction and transaction[0] == 'pending':
                        if st.button(f"Pay Now", key=f"pay_{bid[0]}"):
                            process_payment(bid[0])
            
            st.markdown("---")
    else:
        st.info("No bids placed yet. Browse produce to start bidding!")

def process_payment(bid_id):
    """Process payment for accepted bid"""
    cursor = conn.cursor()
    
    # Get transaction details
    cursor.execute("""
        SELECT t.*, p.title FROM transactions t
        JOIN bids b ON t.bid_id = b.id
        JOIN produce p ON b.produce_id = p.id
        WHERE t.bid_id = ?
    """, (bid_id,))
    transaction = cursor.fetchone()
    
    if transaction:
        st.subheader(f"💳 Payment for: {transaction[8]}")
        st.write(f"**Amount:** ${transaction[5]:.2f}")
        st.write(f"**Transaction ID:** {transaction[1]}")
        
        with st.form(f"payment_form_{bid_id}"):
            payment_method = st.selectbox("Payment Method", [
                "Credit Card", "Debit Card", "Bank Transfer", 
                "Digital Wallet", "UPI", "Cash on Delivery"
            ])
            
            if payment_method in ["Credit Card", "Debit Card"]:
                card_number = st.text_input("Card Number", placeholder="1234 5678 9012 3456")
                col1, col2 = st.columns(2)
                with col1:
                    expiry = st.text_input("Expiry (MM/YY)", placeholder="12/25")
                with col2:
                    cvv = st.text_input("CVV", placeholder="123", type="password")
            
            elif payment_method == "Bank Transfer":
                account_number = st.text_input("Account Number")
                ifsc_code = st.text_input("IFSC Code")
            
            elif payment_method == "UPI":
                upi_id = st.text_input("UPI ID", placeholder="user@bank")
            
            submit_payment = st.form_submit_button("💰 Process Payment")
            
            if submit_payment:
                # Simulate payment processing
                try:
                    cursor.execute("""
                        UPDATE transactions 
                        SET payment_method = ?, payment_status = 'completed'
                        WHERE bid_id = ?
                    """, (payment_method, bid_id))
                    conn.commit()
                    
                    st.success("✅ Payment processed successfully!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Payment failed: {str(e)}")

def transactions_page():
    st.header("💳 Transaction History")
    
    cursor = conn.cursor()
    
    if st.session_state.user_type == 'farmer':
        cursor.execute("""
            SELECT t.*, p.title, u.username as buyer_name
            FROM transactions t
            JOIN bids b ON t.bid_id = b.id
            JOIN produce p ON b.produce_id = p.id
            JOIN users u ON t.buyer_id = u.id
            WHERE t.farmer_id = ?
            ORDER BY t.created_at DESC
        """, (st.session_state.user_id,))
    else:
        cursor.execute("""
            SELECT t.*, p.title, u.username as farmer_name
            FROM transactions t
            JOIN bids b ON t.bid_id = b.id
            JOIN produce p ON b.produce_id = p.id
            JOIN users u ON t.farmer_id = u.id
            WHERE t.buyer_id = ?
            ORDER BY t.created_at DESC
        """, (st.session_state.user_id,))
    
    transactions = cursor.fetchall()
    
    if transactions:
        # Summary metrics
        total_amount = sum(t[5] for t in transactions if t[7] == 'completed')
        completed_transactions = len([t for t in transactions if t[7] == 'completed'])
        pending_transactions = len([t for t in transactions if t[7] == 'pending'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Amount", f"${total_amount:.2f}")
        with col2:
            st.metric("Completed", completed_transactions)
        with col3:
            st.metric("Pending", pending_transactions)
        
        st.markdown("---")
        
        # Transaction list
        for transaction in transactions:
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**Product:** {transaction[8]}")
                st.write(f"**Transaction ID:** {transaction[1]}")
                if st.session_state.user_type == 'farmer':
                    st.write(f"**Buyer:** {transaction[9]}")
                else:
                    st.write(f"**Farmer:** {transaction[9]}")
            
            with col2:
                st.write(f"**Amount:** ${transaction[5]:.2f}")
                st.write(f"**Payment Method:** {transaction[6] or 'Not specified'}")
                st.write(f"**Date:** {transaction[8][:10]}")
            
            with col3:
                status_color = "🟢" if transaction[7] == 'completed' else "🟡" if transaction[7] == 'pending' else "🔴"
                st.write(f"{status_color} {transaction[7].title()}")
            
            st.markdown("---")
    else:
        st.info("No transactions yet.")

def analytics_page():
    st.header("📊 Analytics & Market Trends")
    
    cursor = conn.cursor()
    
    # Market trends data
    if st.session_state.user_type == 'farmer':
        # Farmer analytics
        st.subheader("📈 Your Performance")
        
        # Revenue over time
        cursor.execute("""
            SELECT DATE(t.created_at) as date, SUM(t.amount) as revenue
            FROM transactions t
            WHERE t.farmer_id = ? AND t.payment_status = 'completed'
            GROUP BY DATE(t.created_at)
            ORDER BY date DESC
            LIMIT 30
        """, (st.session_state.user_id,))
        
        revenue_data = cursor.fetchall()
        
        if revenue_data:
            df_revenue = pd.DataFrame(revenue_data, columns=['Date', 'Revenue'])
            fig = px.line(df_revenue, x='Date', y='Revenue', title='Daily Revenue')
            st.plotly_chart(fig, use_container_width=True)
        
        # Category performance
        cursor.execute("""
            SELECT p.category, COUNT(*) as listings, AVG(p.base_price) as avg_price
            FROM produce p
            WHERE p.farmer_id = ?
            GROUP BY p.category
        """, (st.session_state.user_id,))
        
        category_data = cursor.fetchall()
        
        if category_data:
            df_category = pd.DataFrame(category_data, columns=['Category', 'Listings', 'Avg Price'])
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(df_category, values='Listings', names='Category', title='Listings by Category')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(df_category, x='Category', y='Avg Price', title='Average Price by Category')
                st.plotly_chart(fig, use_container_width=True)
    
    else:
        # Buyer analytics
        st.subheader("🛒 Your Buying Patterns")
        
        # Spending over time
        cursor.execute("""
            SELECT DATE(t.created_at) as date, SUM(t.amount) as spending
            FROM transactions t
            WHERE t.buyer_id = ? AND t.payment_status = 'completed'
            GROUP BY DATE(t.created_at)
            ORDER BY date DESC
            LIMIT 30
        """, (st.session_state.user_id,))
        
        spending_data = cursor.fetchall()
        
        if spending_data:
            df_spending = pd.DataFrame(spending_data, columns=['Date', 'Spending'])
            fig = px.line(df_spending, x='Date', y='Spending', title='Daily Spending')
            st.plotly_chart(fig, use_container_width=True)
        
        # Category preferences
        cursor.execute("""
            SELECT p.category, COUNT(*) as bids, AVG(b.bid_amount) as avg_bid
            FROM bids b
            JOIN produce p ON b.produce_id = p.id
            WHERE b.buyer_id = ?
            GROUP BY p.category
        """, (st.session_state.user_id,))
        
        preference_data = cursor.fetchall()
        
        if preference_data:
            df_preference = pd.DataFrame(preference_data, columns=['Category', 'Bids', 'Avg Bid'])
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(df_preference, values='Bids', names='Category', title='Bids by Category')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(df_preference, x='Category', y='Avg Bid', title='Average Bid by Category')
                st.plotly_chart(fig, use_container_width=True)
    
    # Market overview
    st.subheader("🌍 Market Overview")
    
    # Overall market stats
    cursor.execute("SELECT COUNT(*) FROM produce WHERE status = 'active'")
    active_listings = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bids WHERE status = 'pending'")
    pending_bids = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'farmer'")
    total_farmers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'buyer'")
    total_buyers = cursor.fetchone()[0]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Listings", active_listings)
    with col2:
        st.metric("Pending Bids", pending_bids)
    with col3:
        st.metric("Total Farmers", total_farmers)
    with col4:
        st.metric("Total Buyers", total_buyers)
    
    # Price trends by category
    cursor.execute("""
        SELECT category, AVG(base_price) as avg_price, COUNT(*) as listings
        FROM produce
        WHERE status = 'active'
        GROUP BY category
        ORDER BY avg_price DESC
    """)
    
    price_trends = cursor.fetchall()
    
    if price_trends:
        df_trends = pd.DataFrame(price_trends, columns=['Category', 'Avg Price', 'Listings'])
        fig = px.scatter(df_trends, x='Listings', y='Avg Price', size='Listings', 
                        hover_name='Category', title='Price vs Availability by Category')
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
