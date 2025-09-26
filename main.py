import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import plotly.express as px
from PIL import Image
import io

# ---------------------- PAGE CONFIG ----------------------
st.set_page_config(page_title="AgriMarket Pro", page_icon="🌾", layout="wide")

# ---------------------- DATABASE FUNCTIONS ----------------------
def get_connection():
    conn = sqlite3.connect("agrimarket.db", check_same_thread=False)
    return conn

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE,
                 password TEXT,
                 role TEXT
                 )''')
    # Products table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 category TEXT,
                 price REAL,
                 quantity INTEGER,
                 image BLOB,
                 added_on TEXT
                 )''')
    # Purchases table
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT,
                 product_id INTEGER,
                 quantity INTEGER,
                 purchased_on TEXT
                 )''')
    conn.commit()
    conn.close()

# ---------------------- HELPER FUNCTIONS ----------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def save_user(username, password, role="user"):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  (username, hash_password(password), role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password, role FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    if result and verify_password(password, result[0]):
        return result[1]  # Return role
    return None

def add_product(name, category, price, quantity, image):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO products (name, category, price, quantity, image, added_on) VALUES (?, ?, ?, ?, ?, ?)",
              (name, category, price, quantity, image, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_all_products():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    return products

def get_product_by_id(product_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id=?", (product_id,))
    product = c.fetchone()
    conn.close()
    return product

def update_product(product_id, name=None, category=None, price=None, quantity=None):
    conn = get_connection()
    c = conn.cursor()
    if name: c.execute("UPDATE products SET name=? WHERE id=?", (name, product_id))
    if category: c.execute("UPDATE products SET category=? WHERE id=?", (category, product_id))
    if price is not None: c.execute("UPDATE products SET price=? WHERE id=?", (price, product_id))
    if quantity is not None: c.execute("UPDATE products SET quantity=? WHERE id=?", (quantity, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

def add_purchase(username, product_id, quantity):
    product = get_product_by_id(product_id)
    if product and product[4] >= quantity:  # Check stock
        conn = get_connection()
        c = conn.cursor()
        # Update product quantity
        update_product(product_id, quantity=product[4]-quantity)
        # Insert into purchases
        c.execute("INSERT INTO purchases (username, product_id, quantity, purchased_on) VALUES (?, ?, ?, ?)",
                  (username, product_id, quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True
    return False

def get_user_purchases(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT p.id, pr.name, pr.category, p.quantity, pr.price, p.purchased_on "
              "FROM purchases p JOIN products pr ON p.product_id = pr.id "
              "WHERE p.username=?", (username,))
    purchases = c.fetchall()
    conn.close()
    return purchases

def image_to_bytes(image_file):
    return image_file.read() if image_file else None

# ---------------------- INITIALIZATION ----------------------
create_tables()
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = ""

# ---------------------- SIDEBAR ----------------------
st.sidebar.title("AgriMarket Pro 🌾")
menu = st.sidebar.radio("Navigation", ["Home", "Login", "Register", "Admin Panel", "Marketplace", "Analytics", "My Purchases", "Logout"])

# ---------------------- PAGES ----------------------

# ---------------------- HOME PAGE ----------------------
if menu == "Home":
    st.title("Welcome to AgriMarket Pro")
    st.markdown("""
        **AgriMarket Pro** is your one-stop platform to buy and sell agricultural products.
        - Login or Register to start trading.
        - Admins can manage products and view analytics.
        - Users can browse products in Marketplace and track their purchases.
    """)

# ---------------------- REGISTER PAGE ----------------------
elif menu == "Register":
    st.title("User Registration")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["user", "admin"])
    if st.button("Register"):
        if username and password:
            if save_user(username, password, role):
                st.success("Registration successful! You can now login.")
            else:
                st.error("Username already exists.")
        else:
            st.warning("Please fill all fields.")

# ---------------------- LOGIN PAGE ----------------------
elif menu == "Login":
    st.title("User Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        role = authenticate_user(username, password)
        if role:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = role
            st.success(f"Login successful! Role: {role}")
        else:
            st.error("Invalid credentials")

# ---------------------- LOGOUT ----------------------
elif menu == "Logout":
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.success("Logged out successfully.")

# ---------------------- ADMIN PANEL ----------------------
elif menu == "Admin Panel":
    if st.session_state.get("logged_in") and st.session_state.get("role") == "admin":
        st.title("Admin Panel: Manage Products")
        st.subheader("Add New Product")
        name = st.text_input("Product Name")
        category = st.text_input("Category")
        price = st.number_input("Price", min_value=0.0)
        quantity = st.number_input("Quantity", min_value=0)
        image_file = st.file_uploader("Upload Image", type=["png","jpg","jpeg"])
        
        if st.button("Add Product"):
            add_product(name, category, price, quantity, image_to_bytes(image_file))
            st.success("Product added successfully!")
        
        st.subheader("All Products")
        products = get_all_products()
        for p in products:
            cols = st.columns([1,2,2,2,1,1])
            cols[0].write(p[0])
            cols[1].write(p[1])
            cols[2].write(p[2])
            cols[3].write(p[3])
            cols[4].write(p[4])
            if cols[5].button("Delete", key=p[0]):
                delete_product(p[0])
                st.experimental_rerun()
    else:
        st.warning("Admin access required.")

# ---------------------- MARKETPLACE (USER) ----------------------
elif menu == "Marketplace":
    if st.session_state.get("logged_in"):
        st.title("Marketplace: Browse Products")
        products = get_all_products()
        if products:
            df = pd.DataFrame(products, columns=["ID","Name","Category","Price","Quantity","Image","Added_On"])
            categories = ["All"] + df["Category"].unique().tolist()
            selected_category = st.selectbox("Filter by Category", categories)
            
            filtered_df = df if selected_category=="All" else df[df["Category"]==selected_category]
            
            for index, row in filtered_df.iterrows():
                cols = st.columns([2,2,1,1,1])
                # Display image if exists
                if row["Image"]:
                    image = Image.open(io.BytesIO(row["Image"]))
                    cols[0].image(image, width=100)
                else:
                    cols[0].write("No Image")
                cols[1].write(row["Name"])
                cols[2].write(row["Category"])
                cols[3].write(f"₹{row['Price']}")
                qty_to_buy = cols[4].number_input("Qty", min_value=0, max_value=row["Quantity"], key=f"{row['ID']}_qty")
                if cols[4].button("Buy", key=row["ID"]):
                    if qty_to_buy>0:
                        success = add_purchase(st.session_state["username"], row["ID"], qty_to_buy)
                        if success:
                            st.success(f"Purchased {qty_to_buy} of {row['Name']}")
                            st.experimental_rerun()
                        else:
                            st.error("Purchase failed. Not enough stock.")
                    else:
                        st.warning("Enter quantity to buy.")
        else:
            st.info("No products available.")

# ---------------------- USER PURCHASES ----------------------
elif menu == "My Purchases":
    if st.session_state.get("logged_in"):
        st.title("My Purchase History")
        purchases = get_user_purchases(st.session_state["username"])
        if purchases:
            df = pd.DataFrame(purchases, columns=["ID","Product","Category","Quantity","Price","Purchased_On"])
            df["Total_Price"] = df["Quantity"]*df["Price"]
            st.dataframe(df)
        else:
            st.info("No purchases yet.")
    else:
        st.warning("Login required to view purchases.")

# ---------------------- ANALYTICS PAGE ----------------------
elif menu == "Analytics":
    if st.session_state.get("logged_in") and st.session_state.get("role")=="admin":
        st.title("AgriMarket Analytics")
        products = get_all_products()
        if products:
            df = pd.DataFrame(products, columns=["ID","Name","Category","Price","Quantity","Image","Added_On"])
            st.subheader("Product Overview")
            st.dataframe(df.drop(columns="Image"))
            
            st.subheader("Price Distribution by Category")
            fig = px.box(df, x="Category", y="Price", color="Category")
            st.plotly_chart(fig)
            
            st.subheader("Quantity vs Price Scatter")
            fig2 = px.scatter(df, x="Quantity", y="Price", color="Category", size="Price")
            st.plotly_chart(fig2)
        else:
            st.info("No products available for analytics.")
    else:
        st.warning("Admin access required.")
