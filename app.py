from flask import Flask, session, redirect, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # You can use a stronger secret key for production

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'  # This stores the DB file in the same directory
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define a User model for SQLAlchemy
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    balance = db.Column(db.Float, default=1000.0)  # Default balance for new users

# Create the database and tables if they don't exist
db.create_all()

# Preconfigure the admin account with infinite balance if it doesn't exist
@app.before_first_request
def create_admin_account():
    # Check if the 'admin' account exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        # Create the admin user with infinite balance
        admin = User(username='admin', password='adminpassword', balance=float('inf'))
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def home():
    return "Welcome to the cryptocurrency app!"

# Route for user sign up
@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    password = request.form['password']
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "User already exists!"}), 400

    # Create a new user
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User created successfully!"})

# Route for user sign in
@app.route('/signin', methods=['POST'])
def signin():
    username = request.form['username']
    password = request.form['password']
    
    # Check if user exists and the password matches
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session['user_id'] = user.id  # Store user ID in session
        return jsonify({"message": f"Welcome {username}!"})
    
    return jsonify({"error": "Invalid credentials!"}), 400

# Route to view funds (balance)
@app.route('/funds', methods=['GET'])
def view_funds():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in!"}), 401
    
    user = User.query.get(session['user_id'])
    return jsonify({"balance": user.balance})

# Route to transfer funds to another user
@app.route('/transfer', methods=['POST'])
def transfer_funds():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in!"}), 401
    
    sender = User.query.get(session['user_id'])
    recipient_username = request.form['recipient']
    amount = float(request.form['amount'])
    
    # Check if sender has enough balance
    if sender.balance < amount:
        return jsonify({"error": "Insufficient funds!"}), 400
    
    # Find recipient user
    recipient = User.query.filter_by(username=recipient_username).first()
    if not recipient:
        return jsonify({"error": "Recipient not found!"}), 404
    
    # Transfer funds
    sender.balance -= amount
    recipient.balance += amount
    db.session.commit()  # Commit changes to the database
    
    return jsonify({"message": f"Transferred {amount} to {recipient_username}!"})

# Route to withdraw funds (admin only)
@app.route('/withdraw', methods=['POST'])
def withdraw_funds():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in!"}), 401

    user = User.query.get(session['user_id'])
    if user.username != 'admin':  # Ensure only admin can withdraw
        return jsonify({"error": "Only admin can withdraw funds!"}), 403
    
    recipient_username = request.form['recipient']
    amount = float(request.form['amount'])
    
    # Find recipient user
    recipient = User.query.filter_by(username=recipient_username).first()
    if not recipient:
        return jsonify({"error": "Recipient not found!"}), 404
    
    # Deduct the funds from recipient's balance
    recipient.balance -= amount
    db.session.commit()  # Commit changes to the database
    
    return jsonify({"message": f"Withdrawn {amount} from {recipient_username}'s account!"})

# Route to log out the user
@app.route('/logout', methods=['GET'])
def logout():
    session.pop('user_id', None)  # Remove user ID from session
    return jsonify({"message": "Logged out successfully!"})

# Start the app
if __name__ == '__main__':
    app.run(debug=True)
