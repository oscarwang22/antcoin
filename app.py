import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Use the '/tmp' directory for SQLite to persist within the current execution
DATABASE = '/tmp/users.db'

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
                is_admin BOOLEAN NOT NULL DEFAULT FALSE
            )
        ''')
        conn.commit()
        conn.close()


@app.before_first_request
def before_first_request():
    init_db()  # Ensure database and tables are created before the first request is handled


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect(url_for('signup'))

        conn = get_db()
        cursor = conn.cursor()

        # Check if the user is the first user (admin)
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]

        if count == 0:
            # The first user is the admin
            is_admin = True
        else:
            is_admin = False

        try:
            cursor.execute("INSERT INTO users (username, password, balance, is_admin) VALUES (?, ?, ?, ?)",
                           (username, password, 100, is_admin))  # Initial balance 100
            conn.commit()
            flash("Account created successfully!", "success")
            return redirect(url_for('home'))
        except sqlite3.Error as e:
            flash(f"Error: {e}", "error")
            conn.rollback()
        finally:
            conn.close()

    return render_template('signup.html')


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
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password!", "error")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if request.method == 'POST':
        from_user = request.form['from_user']
        to_user = request.form['to_user']
        amount = int(request.form['amount'])

        if from_user == to_user:
            flash("You cannot transfer tokens to yourself.", "error")
            return redirect(url_for('transfer'))

        conn = get_db()
        cursor = conn.cursor()

        # Get balances
        cursor.execute("SELECT balance FROM users WHERE username = ?", (from_user,))
        from_balance = cursor.fetchone()

        cursor.execute("SELECT balance FROM users WHERE username = ?", (to_user,))
        to_balance = cursor.fetchone()

        if not from_balance or not to_balance:
            flash("One or both users do not exist.", "error")
            return redirect(url_for('transfer'))

        # Check if the user has enough balance to transfer
        if from_balance[0] < amount:
            flash("Insufficient balance.", "error")
            return redirect(url_for('transfer'))

        # Perform the transfer
        cursor.execute("UPDATE users SET balance = balance - ? WHERE username = ?", (amount, from_user))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE username = ?", (amount, to_user))
        conn.commit()
        flash("Transfer successful!", "success")
        conn.close()

    return render_template('transfer.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = get_db()
    cursor = conn.cursor()

    # Fetch all users and their details
    cursor.execute("SELECT id, username, balance, is_admin FROM users")
    users = cursor.fetchall()

    if request.method == 'POST':
        action = request.form['action']
        user_id = int(request.form['user_id'])
        new_password = request.form['new_password']
        reset_tokens = request.form['reset_tokens']

        if action == 'reset_password' and new_password:
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_password, user_id))
            conn.commit()
            flash("Password reset successfully!", "success")

        if action == 'reset_tokens' and reset_tokens:
            cursor.execute("UPDATE users SET balance = 100 WHERE id = ?", (user_id,))
            conn.commit()
            flash("Tokens reset to 100 successfully!", "success")

        if action == 'delete_user':
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            flash("User deleted successfully!", "success")

    conn.close()

    return render_template('admin.html', users=users)


if __name__ == "__main__":
    # Initialize the database before starting the application
    init_db()
    app.run(debug=True)
