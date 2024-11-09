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
    # Assuming the user is logged in and their username is stored in the session
    username = session.get('username')
    if username:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username, tokens FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return render_template('index.html', page='home', page_title="Home", username=user[0], tokens=user[1])
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
        from_user = request.form['from_user']
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

        # Check if the sender has enough tokens
        if from_user_data[4] < amount and from_user_data[5] != 1:  # Admin has infinite tokens (tokens field index is 4)
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


if __name__ == "__main__":
    # Initialize the database before starting the application
    init_db()
    app.run(debug=True)
