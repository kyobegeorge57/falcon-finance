from flask import Flask, request, redirect, render_template
import os
from flask import session, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from datetime import datetime

app = Flask(__name__)

# Database configuration for Render
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///Falcon.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
admin = Admin(app, name='Falcon Finance Admin', template_mode='bootstrap3')

UPLOAD_FOLDER = 'static/receipts'
DP_FOLDER = 'static/dp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DP_FOLDER'] = DP_FOLDER

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DP_FOLDER, exist_ok=True)

# User model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    dp = db.Column(db.String(255))

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_submitted = db.Column(db.String(100), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    txn_id = db.Column(db.String(100), nullable=False)
    receipt = db.Column(db.String(255))

# Initialize admin views
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Transaction, db.session))

# Create tables BEFORE the first request
def create_tables():
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

# Call this function to create tables
create_tables()

@app.route('/submit-payment', methods=['POST'])
def submit_payment():
    if 'user_id' not in session:
        return redirect('/index')
    
    try:
        amount = request.form['amount']
        payment_method = request.form['payment_method']
        txn_id = request.form['txn_id']
        receipt = request.files.get('receipt')
        
        filename = None
        if receipt and receipt.filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{session['user_id']}_{timestamp}_{receipt.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            receipt.save(filepath)
        
        user_id = session['user_id']
        
        txn = Transaction(
            user_id=user_id,
            amount=float(amount),
            date_submitted=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            payment_method=payment_method,
            txn_id=txn_id,
            receipt=filename
        )
        
        db.session.add(txn)
        db.session.commit()
        flash('Payment submitted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting payment: {str(e)}', 'error')
        app.logger.error(f'Payment submission error: {str(e)}')
    
    return redirect('/homepage')

@app.route('/signup', methods=['POST'])
def signup():
    try:
        name = request.form['name']
        contact = request.form['contact']
        username = request.form['username']
        password = request.form['password']
        dp = request.files.get('dp')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect('/signup')
        
        dp_filename = None
        if dp and dp.filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            dp_filename = f"{username}_{timestamp}_{dp.filename}"
            dp_path = os.path.join(app.config['DP_FOLDER'], dp_filename)
            dp.save(dp_path)
        
        hashed_password = generate_password_hash(password)
        
        user = User(
            name=name,
            contact=contact,
            username=username,
            password=hashed_password,
            dp=dp_filename
        )
        
        db.session.add(user)
        db.session.commit()
        flash('Signup successful! Please log in.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error during signup: {str(e)}', 'error')
        app.logger.error(f'Signup error: {str(e)}')
        return redirect('/signup')
    
    return redirect('/index')

@app.route('/login', methods=['POST'])
def login():
    try:
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect('/homepage')
        else:
            flash('Invalid username or password', 'error')
            return redirect('/index')
            
    except Exception as e:
        flash(f'Login error: {str(e)}', 'error')
        app.logger.error(f'Login error: {str(e)}')
        return redirect('/index')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/homepage')
def homepage():
    if 'user_id' not in session:
        return redirect('/index')
    
    try:
        user = User.query.get(session['user_id'])
        if user:
            user_data = {
                'name': user.name,
                'contact': user.contact,
                'username': user.username,
                'dp': user.dp
            }
        else:
            user_data = {'name': '', 'contact': '', 'username': '', 'dp': ''}
            
        return render_template('homepage.html', user=user_data)
        
    except Exception as e:
        flash(f'Error loading homepage: {str(e)}', 'error')
        app.logger.error(f'Homepage error: {str(e)}')
        return redirect('/index')

@app.route('/transactions')
def transactions():
    if 'user_id' not in session:
        return redirect('/index')
    
    try:
        txns = Transaction.query.filter_by(user_id=session['user_id']).order_by(Transaction.date_submitted.desc()).all()
        total_paid = sum([float(txn.amount) for txn in txns])
        return render_template('transactions.html', transactions=txns, total_paid=total_paid)
        
    except Exception as e:
        flash(f'Error loading transactions: {str(e)}', 'error')
        app.logger.error(f'Transactions error: {str(e)}')
        return redirect('/homepage')

@app.route('/test')
def test():
    return "Flask is working!"

@app.route('/')
def root():
    return redirect('/index')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect('/index')

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    try:
        # Test database connection
        User.query.limit(1).all()
        return "OK", 200
    except Exception as e:
        return f"Database error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
