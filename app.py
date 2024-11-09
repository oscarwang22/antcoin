import os
import pymongo
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = pymongo.MongoClient(MONGO_URI)
db = client['your_database_name']  # Replace with your database name
users_collection = db['users']     # Collection to store user data

# Helper functions for interacting with MongoDB
def get_user_data(username):
    # Find user by username
    return users_collection.find_one({"username": username})

def set_user_data(username, data):
    # Upsert (insert if not found, update if found) user data
    result = users_collection.update_one({"username": username}, {"$set": data}, upsert=True)
    return result.modified_count > 0 or result.upserted_id is not None

@app.route('/')
def home():
    username = session.get('username')
    if username:
        user_data = get_user_data(username)
        if user_data:
            return render_template(
                'index.html',
                page='home',
                page_title="Home",
                username=user_data['username'],
                tokens=user_data.get('tokens', 0),
                is_admin=user_data.get('is_admin', False)
            )
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

        # Create user data structure
        new_user_data = {
            "username": username,
            "password": password,
            "balance": 100,
            "tokens": 0,
            "is_admin": False  # Regular users are not admins by default
        }

        # Save to MongoDB
        if set_user_data(username, new_user_data):
            flash("Account created successfully!", "success")
            return redirect(url_for('home'))
        else:
            flash("Failed to create account.", "error")
            return redirect(url_for('signup'))

    return render_template('index.html', page='signup', page_title="Sign Up")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_data = get_user_data(username)
        # Check that user_data exists and contains the correct password
        if user_data and user_data.get('password') == password:
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

        from_user_data = get_user_data(from_user_name)
        to_user_data = get_user_data(to_user_name)

        if not from_user_data or not to_user_data:
            flash("One or both users not found!", "error")
            return redirect(url_for('transfer'))

        if from_user_data['tokens'] < amount and not from_user_data['is_admin']:
            flash(f"{from_user_name} does not have enough tokens!", "error")
            return redirect(url_for('transfer'))

        # Update tokens for both users
        from_user_data['tokens'] -= amount
        to_user_data['tokens'] += amount

        # Save updated data back to MongoDB
        set_user_data(from_user_name, from_user_data)
        set_user_data(to_user_name, to_user_data)

        flash(f"Successfully transferred {amount} tokens from {from_user_name} to {to_user_name}.", "success")
        return redirect(url_for('home'))

    return render_template('index.html', page='transfer', page_title="Token Transfer")

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    username = session.get('username')
    user_data = get_user_data(username)
    
    if not user_data or not user_data.get('is_admin'):
        flash("You need to be an admin to access this page.", "error")
        return redirect(url_for('home'))

    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        
        user_data = get_user_data(username)

        if action == 'reset_password':
            new_password = request.form.get('new_password')
            if user_data and new_password:
                user_data['password'] = new_password
                set_user_data(username, user_data)
                flash(f"Password for {username} has been reset.", "success")
            else:
                flash(f"User {username} not found or password is empty.", "error")

        elif action == 'reset_tokens':
            if user_data:
                user_data['tokens'] = 0
                set_user_data(username, user_data)
                flash(f"Tokens for {username} have been reset.", "success")
            else:
                flash(f"User {username} not found.", "error")

    return render_template('index.html', page='admin', page_title="Admin Controls")

@app.route('/api/user_data', methods=['GET'])
def get_user_data_api():
    username = session.get('username')
    if not username:
        return jsonify({"error": "User not logged in"}), 403
    
    user_data = get_user_data(username)
    if user_data:
        return jsonify({
            "username": username,
            "tokens": user_data.get('tokens', 0),
            "balance": user_data.get('balance', 100),
            "is_admin": user_data.get('is_admin', False)
        })
    return jsonify({"error": "User not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
