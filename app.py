from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import os

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# Configure the database connection using Vercel Postgres URL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

# User model for the Postgres database
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    balance = db.Column(db.Integer, default=100)
    tokens = db.Column(db.Integer, default=0)
    is_admin = db.Column(db.Boolean, default=False)

# Initialize database and create the admin user
@app.before_first_request
def init_db():
    db.create_all()
    # Create an admin user if none exists
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', password='adminpassword', balance=100, tokens=99999999, is_admin=True)
        db.session.add(admin_user)
        db.session.commit()

@app.route('/')
def home():
    username = session.get('username')
    if username:
        user = User.query.filter_by(username=username).first()
        if user:
            return render_template('index.html', page='home', page_title="Home", username=user.username, tokens=user.tokens, is_admin=user.is_admin)
        else:
            flash("User not found!", "error")
            return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect(url_for('signup'))

        new_user = User(username=username, password=password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Account created successfully!", "success")
            return redirect(url_for('home'))
        except IntegrityError:
            db.session.rollback()
            flash("Username already taken!", "error")
            return redirect(url_for('signup'))

    return render_template('index.html', page='signup', page_title="Sign Up")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['username'] = username  # Store username in session
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password!", "error")
            return redirect(url_for('login'))

    return render_template('index.html', page='login', page_title="Login")

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if request.method == 'POST':
        from_user_name = session.get('username')
        to_user_name = request.form['to_user']
        amount = int(request.form['amount'])

        if not from_user_name or not to_user_name or amount <= 0:
            flash("All fields are required, and the amount must be greater than 0!", "error")
            return redirect(url_for('transfer'))

        from_user = User.query.filter_by(username=from_user_name).first()
        to_user = User.query.filter_by(username=to_user_name).first()

        if not from_user or not to_user:
            flash("One or both users not found!", "error")
            return redirect(url_for('transfer'))

        if from_user.tokens < amount and not from_user.is_admin:
            flash(f"{from_user_name} does not have enough tokens!", "error")
            return redirect(url_for('transfer'))

        from_user.tokens -= amount
        to_user.tokens += amount
        db.session.commit()

        flash(f"Successfully transferred {amount} tokens from {from_user_name} to {to_user_name}.", "success")
        return redirect(url_for('home'))

    return render_template('index.html', page='transfer', page_title="Token Transfer")

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('username') != 'admin':
        flash("You need to be an admin to access this page.", "error")
        return redirect(url_for('home'))

    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        
        user = User.query.filter_by(username=username).first()

        if action == 'reset_password':
            new_password = request.form.get('new_password')
            if user and new_password:
                user.password = new_password
                db.session.commit()
                flash(f"Password for {username} has been reset.", "success")
            else:
                flash(f"User {username} not found or password is empty.", "error")

        elif action == 'reset_tokens':
            if user:
                user.tokens = 0
                db.session.commit()
                flash(f"Tokens for {username} have been reset.", "success")
            else:
                flash(f"User {username} not found.", "error")

        elif action == 'delete_db':
            confirm = request.form.get('confirm')
            if confirm == 'yes':
                User.query.delete()
                db.session.commit()
                flash("User data deleted successfully.", "info")
                return redirect(url_for('home'))

    return render_template('index.html', page='admin', page_title="Admin Controls")

@app.route('/api/user_data', methods=['GET'])
def get_user_data():
    username = session.get('username')
    if not username:
        return jsonify({"error": "User not logged in"}), 403
    
    user = User.query.filter_by(username=username).first()
    if user:
        return jsonify({
            "username": username,
            "tokens": user.tokens,
            "balance": user.balance,
            "is_admin": user.is_admin
        })
    return jsonify({"error": "User not found"}), 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
