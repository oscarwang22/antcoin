from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'qwertyuioplkjhgfdsssaqazplm'

# Database setup (SQLite)
def get_db():
    conn = sqlite3.connect('crypto_app.db')
    return conn

# Check if user is logged in
def is_logged_in():
    return 'username' in session

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Sign Up
@app.route('/signup', methods=['GET'])
def signup():
    username = request.args.get('username')
    password = request.args.get('password')
    
    if username and password:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, balance) VALUES (?, ?, ?)", (username, password, 100))  # Initial balance 100
        conn.commit()
        conn.close()
        return redirect(url_for('signin'))
    
    return render_template('signup.html')

# Sign In
@app.route('/signin', methods=['GET'])
def signin():
    username = request.args.get('username')
    password = request.args.get('password')
    
    if username and password:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['username'] = username
            return redirect(url_for('funds'))
        else:
            return "Invalid credentials, please try again."
    
    return render_template('signin.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# View Funds
@app.route('/funds')
def funds():
    if is_logged_in():
        username = session['username']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE username = ?", (username,))
        balance = cursor.fetchone()[0]
        conn.close()
        return render_template('funds.html', funds=balance)
    
    return redirect(url_for('signin'))

# Transfer Funds
@app.route('/transfer', methods=['GET'])
def transfer():
    if is_logged_in():
        recipient = request.args.get('recipient')
        amount = float(request.args.get('amount'))
        
        if recipient and amount > 0:
            sender = session['username']
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE username = ?", (sender,))
            sender_balance = cursor.fetchone()[0]
            
            if sender_balance >= amount:
                cursor.execute("UPDATE users SET balance = balance - ? WHERE username = ?", (amount, sender))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE username = ?", (amount, recipient))
                conn.commit()
                conn.close()
                return redirect(url_for('funds'))
            else:
                return "Insufficient funds."
        
    return redirect(url_for('signin'))

if __name__ == '__main__':
    app.run(debug=True)
