from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
from PIL import Image
import io
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agri_marketplace.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'farmer' or 'buyer'
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Produce(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)  # kg, tons, bags, etc.
    base_price = db.Column(db.Float, nullable=False)
    quality_grade = db.Column(db.String(10))  # A, B, C, Premium
    harvest_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    location = db.Column(db.String(100))
    image_path = db.Column(db.String(200))
    status = db.Column(db.String(20), default='active')  # active, sold, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    farmer = db.relationship('User', backref='produce_listings')

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bid_amount = db.Column(db.Float, nullable=False)
    quantity_requested = db.Column(db.Float, nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    produce = db.relationship('Produce', backref='bids')
    buyer = db.relationship('User', backref='bids_made')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)
    bid_id = db.Column(db.Integer, db.ForeignKey('bid.id'), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    bid = db.relationship('Bid', backref='transaction')

# AI-based Quality Grading (Simplified simulation)
def analyze_produce_quality(image_data):
    """
    Simplified quality analysis - in production, integrate with actual AI models
    like TensorFlow, OpenCV, or cloud vision APIs
    """
    # This is a placeholder - replace with actual AI image analysis
    import random
    grades = ['Premium', 'A', 'B', 'C']
    confidence_scores = [95, 88, 75, 60]
    
    grade_index = random.randint(0, 3)
    return {
        'grade': grades[grade_index],
        'confidence': confidence_scores[grade_index],
        'defects': random.choice(['None', 'Minor spots', 'Small bruises', 'Color variations']),
        'freshness_score': random.randint(70, 100)
    }

# Routes
@app.route('/')
def home():
    recent_produce = Produce.query.filter_by(status='active').order_by(Produce.created_at.desc()).limit(6).all()
    return render_template('home.html', recent_produce=recent_produce)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.json
        
        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            user_type=data['user_type'],
            phone=data.get('phone', ''),
            address=data.get('address', '')
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'message': 'Registration successful'}), 201
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        user = User.query.filter_by(email=data['email']).first()
        
        if user and check_password_hash(user.password_hash, data['password']):
            session['user_id'] = user.id
            session['user_type'] = user.user_type
            return jsonify({'message': 'Login successful', 'redirect': '/dashboard'}), 200
        
        return jsonify({'error': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if user.user_type == 'farmer':
        produce_listings = Produce.query.filter_by(farmer_id=user.id).all()
        recent_bids = Bid.query.join(Produce).filter(Produce.farmer_id == user.id).order_by(Bid.created_at.desc()).limit(10).all()
        return render_template('farmer_dashboard.html', user=user, produce_listings=produce_listings, recent_bids=recent_bids)
    else:
        recent_bids = Bid.query.filter_by(buyer_id=user.id).order_by(Bid.created_at.desc()).limit(10).all()
        return render_template('buyer_dashboard.html', user=user, recent_bids=recent_bids)

@app.route('/add_produce', methods=['GET', 'POST'])
def add_produce():
    if 'user_id' not in session or session['user_type'] != 'farmer':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = request.form
        
        # Handle image upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_path = filename
                
                # Analyze quality using AI (simulated)
                with open(file_path, 'rb') as img_file:
                    img_data = img_file.read()
                quality_analysis = analyze_produce_quality(img_data)
                quality_grade = quality_analysis['grade']
        else:
            quality_grade = 'Not Graded'
        
        produce = Produce(
            farmer_id=session['user_id'],
            title=data['title'],
            description=data['description'],
            category=data['category'],
            quantity=float(data['quantity']),
            unit=data['unit'],
            base_price=float(data['base_price']),
            quality_grade=quality_grade,
            harvest_date=datetime.strptime(data['harvest_date'], '%Y-%m-%d').date(),
            expiry_date=datetime.strptime(data['expiry_date'], '%Y-%m-%d').date(),
            location=data['location'],
            image_path=image_path
        )
        
        db.session.add(produce)
        db.session.commit()
        
        return redirect(url_for('dashboard'))
    
    return render_template('add_produce.html')

@app.route('/browse')
def browse_produce():
    category = request.args.get('category', '')
    location = request.args.get('location', '')
    quality = request.args.get('quality', '')
    
    query = Produce.query.filter_by(status='active')
    
    if category:
        query = query.filter(Produce.category == category)
    if location:
        query = query.filter(Produce.location.contains(location))
    if quality:
        query = query.filter(Produce.quality_grade == quality)
    
    produce_list = query.order_by(Produce.created_at.desc()).all()
    categories = db.session.query(Produce.category).distinct().all()
    qualities = db.session.query(Produce.quality_grade).distinct().all()
    
    return render_template('browse.html', produce_list=produce_list, categories=categories, qualities=qualities)

@app.route('/produce/<int:produce_id>')
def produce_detail(produce_id):
    produce = Produce.query.get_or_404(produce_id)
    bids = Bid.query.filter_by(produce_id=produce_id).order_by(Bid.bid_amount.desc()).all()
    return render_template('produce_detail.html', produce=produce, bids=bids)

@app.route('/place_bid', methods=['POST'])
def place_bid():
    if 'user_id' not in session or session['user_type'] != 'buyer':
        return jsonify({'error': 'Login required as buyer'}), 401
    
    data = request.json
    
    bid = Bid(
        produce_id=data['produce_id'],
        buyer_id=session['user_id'],
        bid_amount=float(data['bid_amount']),
        quantity_requested=float(data['quantity_requested']),
        message=data.get('message', '')
    )
    
    db.session.add(bid)
    db.session.commit()
    
    return jsonify({'message': 'Bid placed successfully'}), 201

@app.route('/accept_bid/<int:bid_id>', methods=['POST'])
def accept_bid(bid_id):
    if 'user_id' not in session or session['user_type'] != 'farmer':
        return jsonify({'error': 'Access denied'}), 403
    
    bid = Bid.query.get_or_404(bid_id)
    
    # Check if farmer owns the produce
    if bid.produce.farmer_id != session['user_id']:
        return jsonify({'error': 'Access denied'}), 403
    
    bid.status = 'accepted'
    
    # Create transaction
    transaction = Transaction(
        transaction_id=f"TXN_{uuid.uuid4().hex[:8]}",
        bid_id=bid.id,
        farmer_id=session['user_id'],
        buyer_id=bid.buyer_id,
        amount=bid.bid_amount * bid.quantity_requested,
        payment_method='pending'
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({'message': 'Bid accepted', 'transaction_id': transaction.transaction_id}), 200

@app.route('/process_payment/<transaction_id>', methods=['POST'])
def process_payment(transaction_id):
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first_or_404()
    data = request.json
    
    # Simulate payment processing
    transaction.payment_method = data['payment_method']
    transaction.payment_status = 'completed'  # In real app, integrate with payment gateway
    
    # Update produce status if fully sold
    bid = transaction.bid
    if bid.quantity_requested >= bid.produce.quantity:
        bid.produce.status = 'sold'
    
    db.session.commit()
    
    return jsonify({'message': 'Payment processed successfully'}), 200

@app.route('/transactions')
def transactions():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session['user_type'] == 'farmer':
        transactions = Transaction.query.filter_by(farmer_id=session['user_id']).order_by(Transaction.created_at.desc()).all()
    else:
        transactions = Transaction.query.filter_by(buyer_id=session['user_id']).order_by(Transaction.created_at.desc()).all()
    
    return render_template('transactions.html', transactions=transactions)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Initialize database
@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    # Create upload directory
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    app.run(debug=True)
