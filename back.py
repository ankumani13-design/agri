import sqlite3, hashlib
from datetime import datetime

DB_NAME = "agrimarket.db"

# ----------------- DB CONNECTION -----------------
def get_connection(): 
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# ----------------- TABLE CREATION -----------------
def create_tables():
    conn = get_connection()
    c = conn.cursor()
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE,
                 password TEXT,
                 role TEXT)''')
    # Products table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 category TEXT,
                 price REAL,
                 quantity INTEGER,
                 image BLOB,
                 added_by TEXT,
                 added_on TEXT)''')
    # Purchases table
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT,
                 product_id INTEGER,
                 quantity INTEGER,
                 purchased_on TEXT)''')
    conn.commit()
    conn.close()

# ----------------- AUTHENTICATION -----------------
def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()
def verify_password(password, hashed): return hash_password(password) == hashed

def save_user(username,password,role="user"):
    conn=get_connection(); c=conn.cursor()
    try:
        c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                  (username, hash_password(password), role))
        conn.commit()
        return True
    except sqlite3.IntegrityError: return False
    finally: conn.close()

def authenticate_user(username,password):
    conn=get_connection(); c=conn.cursor()
    c.execute("SELECT password,role FROM users WHERE username=?",(username,))
    result=c.fetchone(); conn.close()
    if result and verify_password(password,result[0]): return result[1]
    return None

# ----------------- PRODUCT FUNCTIONS -----------------
def add_product(name, category, price, quantity, image_bytes, added_by):
    conn=get_connection(); c=conn.cursor()
    c.execute('''INSERT INTO products (name,category,price,quantity,image,added_by,added_on)
                 VALUES (?,?,?,?,?,?,?)''',
              (name, category, price, quantity, image_bytes, added_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()

def get_all_products():
    conn=get_connection(); c=conn.cursor(); c.execute("SELECT * FROM products"); products=c.fetchall(); conn.close(); return products

def get_products_by_user(username):
    conn=get_connection(); c=conn.cursor()
    c.execute("SELECT * FROM products WHERE added_by=?",(username,))
    products=c.fetchall(); conn.close(); return products

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

# ----------------- PURCHASE FUNCTIONS -----------------
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
    c.execute('''SELECT p.id, pr.name, pr.category, p.quantity, pr.price, p.purchased_on
                 FROM purchases p JOIN products pr ON p.product_id=pr.id
                 WHERE p.username=?''',(username,))
    purchases=c.fetchall(); conn.close(); return purchases
