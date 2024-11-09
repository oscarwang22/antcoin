from flask import Flask, request, jsonify, session
import hashlib
import json
import os

app = Flask(__name__)
app.secret_key = 'asdfghjklpoiuytrewqqazplzxcvbnm'  # Replace with a secure secret key for session management

# Paths for user and transaction data
DATA_DIR = '/data'
USER_DATA_FILE = os.path.join(DATA_DIR, 'users.json')
TRANSACTION_DATA_FILE = os.path.join(DATA_DIR, 'transactions.json')

# Load data from JSON files
if os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, 'r') as f:
        users = json.load(f)
else:
    users = {}

if os.path.exists(TRANSACTION_DATA_FILE):
    with open(TRANSACTION_DATA_FILE, 'r') as f:
        transactions = json.load(f)
else:
    transactions = {}

admin_password = "11234"  # Password to access admin endpoints
admin_balance = float('inf')  # Infinite balance for the admin

def save_data():
    """Save users and transactions data to JSON files."""
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f)
    with open(TRANSACTION_DATA_FILE, 'w') as f:
        json.dump(transactions, f)

@app.route('/signup', methods=['GET'])
def signup():
    username = request.args.get('username')
    password = request.args.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if username in users:
        return jsonify({"error": "Username already taken"}), 400

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    users[username] = {"password": hashed_password, "balance": 0.0}
    transactions[username] = []
    save_data()  # Save data after signup
    return jsonify({"message": f"User {username} created successfully!"})

@app.route('/signin', methods=['GET'])
def signin():
    username = request.args.get('username')
    password = request.args.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if username not in users:
        return jsonify({"error": "User not found"}), 404

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    if users[username]["password"] != hashed_password:
        return jsonify({"error": "Incorrect password"}), 401

    session['user_id'] = username
    return jsonify({"message": f"Logged in as {username}."})

# Add the other routes (like /funds, /transfer, /admin/transfer, /admin/withdraw, etc.)

@app.route('/transactions', methods=['GET'])
def view_transactions():
    if 'user_id' not in session:
        return jsonify({"error": "You must be logged in to view your transactions."}), 401
    
    username = session['user_id']
    user_transactions = transactions.get(username, [])
    return jsonify({"transactions": user_transactions})

if __name__ == '__main__':
    app.run(debug=True)
