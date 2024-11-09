import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'users.db'  # SQLite database file

# Function to get a database connection
def get_db():
    conn = sqlite3.connect(DATABASE)
    return conn

# Create users table if it doesn't exist
def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                balance INTEGER NOT NULL DEFAULT 100,
                tokens INTEGER NOT NULL DEFAULT 0,
                is_admin BOOLEAN NOT NULL DEFAULT 0
            )
        ''')
        conn.commit()

        # Set the first user as admin
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        if user_count == 0:
            cursor.execute("INSERT INTO users (username, password, balance, tokens, is_admin) VALUES (?, ?, ?, ?, ?)",
                           ('admin', 'adminpassword', 100, 99999999, 1))  # Create an admin user with infinite tokens
            conn.commit()

        conn.close()

@app.before_first_request
def before_first_request():
    init_db()  # Ensure database and tables are created before the first request is handled

@app.route('/')
def home():
    username = session.get('username')
    if username:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username, tokens FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return render_template('index.html', page='home', page_title="Home", username=user[0], tokens=user[1], is_admin=user[1] == 'admin')
        else:
            flash("User not found!", "error")
            return redirect(url_for('home'))
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

        # Insert the new user into the database
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, balance, tokens) VALUES (?, ?, ?, ?)",
                           (username, password, 100, 0))  # Initial balance 100, no tokens
            conn.commit()
            flash("Account created successfully!", "success")
            return redirect(url_for('home'))
        except sqlite3.Error as e:
            flash(f"Error: {e}", "error")
            conn.rollback()
        finally:
            conn.close()

    return render_template('index.html', page='signup', page_title="Sign Up")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect(url_for('login'))

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

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
        from_user = session.get('username')
        to_user = request.form['to_user']
        amount = int(request.form['amount'])

        if not from_user or not to_user or amount <= 0:
            flash("All fields are required, and the amount must be greater than 0!", "error")
            return redirect(url_for('transfer'))

        conn = get_db()
        cursor = conn.cursor()

        # Get the users' token balances
        cursor.execute("SELECT * FROM users WHERE username = ?", (from_user,))
        from_user_data = cursor.fetchone()
        cursor.execute("SELECT * FROM users WHERE username = ?", (to_user,))
        to_user_data = cursor.fetchone()

        if not from_user_data:
            flash(f"User {from_user} not found!", "error")
            return redirect(url_for('transfer'))
        
        if not to_user_data:
            flash(f"User {to_user} not found!", "error")
            return redirect(url_for('transfer'))

        # Regular users can only transfer their own tokens
        if from_user_data[4] < amount and from_user_data[5] != 1:  # Admin has infinite tokens
            flash(f"{from_user} does not have enough tokens!", "error")
            return redirect(url_for('transfer'))

        # Proceed with the transfer
        if from_user_data[5] != 1:  # Admin is not included in this check
            cursor.execute("UPDATE users SET tokens = tokens - ? WHERE username = ?", (amount, from_user))
        cursor.execute("UPDATE users SET tokens = tokens + ? WHERE username = ?", (amount, to_user))
        conn.commit()
        conn.close()

        flash(f"Successfully transferred {amount} tokens from {from_user} to {to_user}.", "success")
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
        
        conn = get_db()
        cursor = conn.cursor()

        if action == 'reset_password':
            new_password = request.form.get('new_password')
            if not new_password:
                flash("New password is required.", "error")
                return redirect(url_for('admin'))

            cursor.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
            conn.commit()
            flash(f"Password for {username} has been reset.", "success")

        elif action == 'reset_tokens':
            cursor.execute("UPDATE users SET tokens = 0 WHERE username = ?", (username,))
            conn.commit()
            flash(f"Tokens for {username} have been reset.", "success")

        elif action == 'delete_db':
            confirm = request.form.get('confirm')
            if confirm == 'yes':
                os.remove(DATABASE)
                flash("Database deleted successfully. You will need to recreate the app.", "info")
                return redirect(url_for('home'))

        conn.close()

    return render_template('index.html', page='admin', page_title="Admin Controls")


@app.route('/export_json', methods=['GET'])
def export_json():
    if session.get('username') != 'admin':
        flash("You need to be an admin to access this page.", "error")
        return redirect(url_for('home'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, tokens FROM users")
    users = cursor.fetchall()
    conn.close()

    # Prepare data in dictionary form
    user_data = [{"username": user[0], "tokens": user[1]} for user in users]

    # Save the data to /tmp/users.json
    export_path = '/tmp/users.json'
    with open(export_path, 'w') as f:
        json.dump(user_data, f)

    flash(f"User data exported successfully to {export_path}.", "success")
    return redirect(url_for('admin'))


if __name__ == "__main__":
    # Initialize the database before starting the application
    init_db()
    app.run(debug=True)
