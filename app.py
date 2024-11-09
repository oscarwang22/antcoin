from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import vercel_kv

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# Initialize Vercel KV client
kv = vercel_kv.Client(token=os.getenv('VERCEL_KV_TOKEN'))

# Helper functions for user data operations
def get_user(username):
    user_data = kv.get(f"user:{username}")
    return user_data

def set_user(user_data):
    kv.set(f"user:{user_data['username']}", user_data)

def delete_user(username):
    kv.delete(f"user:{username}")

@app.route('/')
def home():
    username = session.get('username')
    if username:
        user = get_user(username)
        if user:
            return render_template('index.html', page='home', page_title="Home", username=user['username'], tokens=user['tokens'], is_admin=user['is_admin'])
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

        if get_user(username):
            flash("Username already taken!", "error")
            return redirect(url_for('signup'))

        # Create new user
        new_user = {
            'username': username,
            'password': password,
            'balance': 100,
            'tokens': 0,
            'is_admin': False
        }
        set_user(new_user)
        flash("Account created successfully!", "success")
        return redirect(url_for('home'))

    return render_template('index.html', page='signup', page_title="Sign Up")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = get_user(username)
        if user and user['password'] == password:
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

        from_user = get_user(from_user_name)
        to_user = get_user(to_user_name)

        if not from_user or not to_user:
            flash("One or both users not found!", "error")
            return redirect(url_for('transfer'))

        if from_user['tokens'] < amount and not from_user['is_admin']:
            flash(f"{from_user_name} does not have enough tokens!", "error")
            return redirect(url_for('transfer'))

        # Update token balances
        from_user['tokens'] -= amount
        to_user['tokens'] += amount
        set_user(from_user)
        set_user(to_user)

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
        
        user = get_user(username)

        if action == 'reset_password':
            new_password = request.form.get('new_password')
            if user and new_password:
                user['password'] = new_password
                set_user(user)
                flash(f"Password for {username} has been reset.", "success")
            else:
                flash(f"User {username} not found or password is empty.", "error")

        elif action == 'reset_tokens':
            if user:
                user['tokens'] = 0
                set_user(user)
                flash(f"Tokens for {username} have been reset.", "success")
            else:
                flash(f"User {username} not found.", "error")

        elif action == 'delete_db':
            confirm = request.form.get('confirm')
            if confirm == 'yes':
                kv.clear()
                flash("All user data deleted successfully.", "info")
                return redirect(url_for('home'))

    return render_template('index.html', page='admin', page_title="Admin Controls")

@app.route('/api/user_data', methods=['GET'])
def get_user_data():
    username = session.get('username')
    if not username:
        return jsonify({"error": "User not logged in"}), 403
    
    user = get_user(username)
    if user:
        return jsonify({
            "username": username,
            "tokens": user['tokens'],
            "balance": user['balance'],
            "is_admin": user['is_admin']
        })
    return jsonify({"error": "User not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
