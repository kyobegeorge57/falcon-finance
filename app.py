from flask import Flask, request, redirect, render_template
import os
from flask import session, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Falcon.db'
app.config['SECRET_KEY'] = 'your-secret-key'

db = SQLAlchemy(app)
admin = Admin(app, name='Falcon Finance Admin', template_mode='bootstrap3')

UPLOAD_FOLDER = 'static/receipts'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# User model matching your SQLite schema
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

admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Transaction, db.session))

@app.route('/submit-payment', methods=['POST'])
def submit_payment():
    if 'user_id' not in session:
        return redirect('/index')
    amount = request.form['amount']
    payment_method = request.form['payment_method']
    txn_id = request.form['txn_id']
    receipt = request.files['receipt']
    filename = None
    if receipt:
        filename = os.path.join(app.config['UPLOAD_FOLDER'], receipt.filename)
        receipt.save(filename)
    user_id = session['user_id']
    from datetime import datetime
    txn = Transaction(
        user_id=user_id,
        amount=amount,
        date_submitted=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        payment_method=payment_method,
        txn_id=txn_id,
        receipt=filename
    )
    db.session.add(txn)
    db.session.commit()
    flash('Payment submitted successfully!')
    return redirect('/homepage')

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    contact = request.form['contact']
    username = request.form['username']
    password = request.form['password']
    dp = request.files['dp']
    dp_filename = None
    if dp:
        dp_filename = os.path.join('static/dp', dp.filename)
        os.makedirs('static/dp', exist_ok=True)
        dp.save(dp_filename)
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
    flash('Signup successful! Please log in.')
    return redirect('/index')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['username'] = username
        return redirect('/homepage')
    else:
        flash('Invalid username or password')
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

@app.route('/transactions')
def transactions():
    if 'user_id' not in session:
        return redirect('/index')
    txns = Transaction.query.filter_by(user_id=session['user_id']).order_by(Transaction.date_submitted.desc()).all()
    total_paid = sum([float(txn.amount) for txn in txns])
    return render_template('transactions.html', transactions=txns, total_paid=total_paid)

@app.route('/test')
def test():
    return "Flask is working!"

@app.route('/')
def root():
    return redirect('/index')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)