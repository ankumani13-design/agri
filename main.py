import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd
import plotly.express as px
from PIL import Image
import io

# ----------------- PAGE CONFIG -----------------
st.set_page_config(page_title="Welcome to AgriMarket", page_icon="🌾", layout="wide")

# ----------------- CUSTOM CSS -----------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {background-color: #f0f4f8; font-family: 'Segoe UI', sans-serif;}
.top-header {display:flex;justify-content:space-between;align-items:center;background-color:#2E8B57;color:white;padding:15px 30px;border-radius:12px;margin-bottom:20px;}
.app-title {font-size:28px;font-weight:bold;}
.top-right {font-size:16px;font-weight:bold;}
.centered-title {text-align:center;font-size:36px;font-weight:bold;color:#2E8B57;margin-bottom:20px;}
div[role="radiogroup"] {display:flex;justify-content:center;gap:20px;margin-bottom:30px;}
.css-1v3fvcr.e1fqkh3o1 { flex-direction: row; }
[data-baseweb="radio"] label {font-weight:bold;font-size:16px;padding:10px 20px;background-color:#e0e0e0;border-radius:12px;transition:0.3s;}
[data-baseweb="radio"] input:checked + label {background-color:#2E8B57;color:white;}
[data-baseweb="radio"] label:hover {background-color:#3cb371;color:white;cursor:pointer;}
.product-card {background-color:white;padding:10px;border-radius:12px;box-shadow:0 4px 8px rgba(0,0,0,0.1);transition:0.3s;margin-bottom:20px;text-align:center;}
.product-card:hover {box-shadow:0 8px 16px rgba(0,0,0,0.2);}
.product-card img {border-radius:12px;margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

# ----------------- DATABASE FUNCTIONS -----------------
def get_connection(): return sqlite3.connect("agrimarket.db", check_same_thread=False)

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE,
                 password TEXT,
                 role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 category TEXT,
                 price REAL,
                 quantity INTEGER,
                 image BLOB,
                 added_on TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT,
                 product_id INTEGER,
                 quantity INTEGER,
                 purchased_on TEXT)''')
    conn.commit()
    conn.close()

# ----------------- HELPER FUNCTIONS -----------------
def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()
def verify_password(password, hashed): return hash_password(password) == hashed
def save_user(username, password, role="user"):
    conn = get_connection(); c = conn.cursor()
    try: c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",(username,hash_password(password),role)); conn.commit(); return True
    except sqlite3.IntegrityError: return False
    finally: conn.close()

def authenticate_user(username,password):
    conn=get_connection(); c=conn.cursor()
    c.execute("SELECT password, role FROM users WHERE username=?",(username,))
    result=c.fetchone(); conn.close()
    if result and verify_password(password,result[0]): return result[1]
    return None

def add_product(name,category,price,quantity,image):
    conn=get_connection(); c=conn.cursor()
    c.execute("INSERT INTO products (name,category,price,quantity,image,added_on) VALUES (?,?,?,?,?,?)",
              (name,category,price,quantity,image,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()

def get_all_products():
    conn=get_connection(); c=conn.cursor(); c.execute("SELECT * FROM products"); products=c.fetchall(); conn.close(); return products

def get_product_by_id(pid):
    conn=get_connection(); c=conn.cursor(); c.execute("SELECT * FROM products WHERE id=?",(pid,)); p=c.fetchone(); conn.close(); return p

def update_product(pid,name=None,category=None,price=None,quantity=None):
    conn=get_connection(); c=conn.cursor()
    if name: c.execute("UPDATE products SET name=? WHERE id=?",(name,pid))
    if category: c.execute("UPDATE products SET category=? WHERE id=?",(category,pid))
    if price is not None: c.execute("UPDATE products SET price=? WHERE id=?",(price,pid))
    if quantity is not None: c.execute("UPDATE products SET quantity=? WHERE id=?",(quantity,pid))
    conn.commit(); conn.close()

def delete_product(pid):
    conn=get_connection(); c=conn.cursor(); c.execute("DELETE FROM products WHERE id=?",(pid,)); conn.commit(); conn.close()

def add_purchase(username,pid,qty):
    product=get_product_by_id(pid)
    if product and product[4]>=qty:
        update_product(pid,quantity=product[4]-qty)
        conn=get_connection(); c=conn.cursor()
        c.execute("INSERT INTO purchases (username,product_id,quantity,purchased_on) VALUES (?,?,?,?)",
                  (username,pid,qty,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close(); return True
    return False

def get_user_purchases(username):
    conn=get_connection(); c=conn.cursor()
    c.execute("SELECT p.id, pr.name, pr.category, p.quantity, pr.price, p.purchased_on FROM purchases p JOIN products pr ON p.product_id=pr.id WHERE p.username=?",(username,))
    purchases=c.fetchall(); conn.close(); return purchases

def image_to_bytes(image_file): return image_file.read() if image_file else None

# ----------------- INITIALIZATION -----------------
create_tables()
if "logged_in" not in st.session_state: st.session_state["logged_in"]=False
if "username" not in st.session_state: st.session_state["username"]=""
if "role" not in st.session_state: st.session_state["role"]=""
if "cart" not in st.session_state: st.session_state["cart"]={}

# ----------------- TOP HEADER -----------------
header_html=f"""
<div class="top-header">
  <div class="app-title">🌾 AgriMarket Pro</div>
  <div class="top-right">{"Welcome, "+st.session_state['username'].title() if st.session_state.get("logged_in") else "Not Logged In"}</div>
</div>
"""
st.markdown(header_html,unsafe_allow_html=True)
st.markdown('<div class="centered-title">Welcome to AgriMarket Pro 🌾</div>',unsafe_allow_html=True)

# ----------------- NAVIGATION -----------------
tabs=["Home","Login","Register","Admin Panel","Marketplace","Cart","My Purchases","Analytics","Logout"]
menu=st.radio("",tabs,index=0,horizontal=True)

# ----------------- PAGES -----------------
if menu=="Home":
    st.write("AgriMarket Pro is your modern platform to buy & sell agricultural products efficiently!")

elif menu=="Register":
    st.header("User Registration")
    username=st.text_input("Username")
    password=st.text_input("Password",type="password")
    role=st.selectbox("Role",["user","admin"])
    if st.button("Register"):
        if username and password:
            if save_user(username,password,role): st.success("Registration successful! Login now.")
            else: st.error("Username already exists.")

elif menu=="Login":
    st.header("Login")
    username=st.text_input("Username")
    password=st.text_input("Password",type="password")
    if st.button("Login"):
        role=authenticate_user(username,password)
        if role:
            st.session_state["logged_in"]=True
            st.session_state["username"]=username
            st.session_state["role"]=role
            st.success(f"Login successful! Role: {role}")
        else: st.error("Invalid credentials")

elif menu=="Logout":
    st.session_state["logged_in"]=False
    st.session_state["username"]=""
    st.session_state["role"]=""
    st.session_state["cart"]={}
    st.success("Logged out successfully.")

elif menu=="Admin Panel":
    if st.session_state.get("logged_in") and st.session_state.get("role")=="admin":
        st.header("Admin Panel")
        st.subheader("Add Product")
        name=st.text_input("Product Name")
        category=st.text_input("Category")
        price=st.number_input("Price",min_value=0.0)
        quantity=st.number_input("Quantity",min_value=0)
        image_file=st.file_uploader("Upload Image", type=["png","jpg","jpeg"])
        if st.button("Add Product"):
            add_product(name,category,price,quantity,image_to_bytes(image_file))
            st.success("Product added successfully!")
        st.subheader("All Products")
        products=get_all_products()
        for p in products:
            cols=st.columns([1,2,2,2,1,1])
            cols[0].write(p[0]); cols[1].write(p[1]); cols[2].write(p[2]); cols[3].write(p[3]); cols[4].write(p[4])
            if cols[5].button("Delete",key=p[0]):
                delete_product(p[0]); st.experimental_rerun()
    else: st.warning("Admin access required.")

elif menu=="Marketplace":
    if st.session_state.get("logged_in"):
        st.header("Marketplace")
        products=get_all_products()
        if products:
            df=pd.DataFrame(products,columns=["ID","Name","Category","Price","Quantity","Image","Added_On"])
            categories=["All"]+df["Category"].unique().tolist()
            selected_category=st.selectbox("Filter by Category",categories)
            filtered_df=df if selected_category=="All" else df[df["Category"]==selected_category]
            cols_per_row=3
            for i in range(0,len(filtered_df),cols_per_row):
                cols=st.columns(cols_per_row)
                for idx,row in enumerate(filtered_df.iloc[i:i+cols_per_row].itertuples()):
                    with cols[idx]:
                        st.markdown('<div class="product-card">',unsafe_allow_html=True)
                        st.image(Image.open(io.BytesIO(row.Image)) if row.Image else None,use_column_width=True)
                        st.markdown(f"**{row.Name}**"); st.write(f"Category: {row.Category}"); st.write(f"Price: ₹{row.Price}")
                        qty_to_add=st.number_input("Qty",min_value=0,max_value=row.Quantity,key=f"{row.ID}_market_qty")
                        if st.button("Add to Cart",key=f"{row.ID}_market_btn"):
                            if qty_to_add>0:
                                st.session_state["cart"][row.ID]=st.session_state["cart"].get(row.ID,0)+qty_to_add
                                st.success(f"Added {qty_to_add} of {row.Name} to cart")
                                st.experimental_rerun()
                            else: st.warning("Enter quantity to add.")
                        st.markdown('</div>',unsafe_allow_html=True)

elif menu=="Cart":
    st.header("Your Cart")
    if st.session_state.get("cart"):
        cart_items=st.session_state["cart"]; total_price=0
        for pid,qty in cart_items.items():
            product=get_product_by_id(pid)
            if product: st.write(f"{product[1]} ({qty} units) - ₹{product[3]*qty}"); total_price+=product[3]*qty
        st.write(f"**Total: ₹{total_price}**")
        if st.button("Checkout"):
            for pid,qty in cart_items.items(): add_purchase(st.session_state["username"],pid,qty)
            st.session_state["cart"]={}; st.success("Checkout successful!")
    else: st.info("Your cart is empty.")

elif menu=="My Purchases":
    st.header("My Purchases")
    purchases=get_user_purchases(st.session_state["username"])
    if purchases:
        for p in purchases: st.write(f"{p[1]} | Qty: {p[3]} | Price per unit: ₹{p[4]} | Purchased on: {p[5]}")
    else: st.info("No purchases yet.")

elif menu=="Analytics":
    if st.session_state.get("logged_in") and st.session_state.get("role")=="admin":
        st.header("Analytics")
        products=get_all_products()
        if products:
            df=pd.DataFrame(products,columns=["ID","Name","Category","Price","Quantity","Image","Added_On"])
            fig=px.bar(df,x="Name",y="Quantity",color="Category",title="Product Stock")
            st.plotly_chart(fig)
        purchases=pd.read_sql("SELECT p.id, pr.Name, p.quantity, pr.Price, p.purchased_on FROM purchases p JOIN products pr ON p.product_id=pr.id",get_connection())
        if not purchases.empty:
            purchases['Total']=purchases['quantity']*purchases['Price']
            fig2=px.bar(purchases,x="Name",y="Total",title="Sales Revenue")
            st.plotly_chart(fig2)
    else: st.warning("Admin access required.")
