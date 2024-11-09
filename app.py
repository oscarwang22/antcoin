from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import os
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'

USERS_FILE = '/tmp/users.json'  # Path to the JSON file

# Function to load users from the JSON file
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Function to save users to the JSON file
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Initialize the user data (creates an admin user if file doesn't exist)
def init_users():
    if not os.path.exists(USERS_FILE):
        users = {}
        users['admin'] = {
            'password': 'adminpassword',
            'balance': 100,
            'tokens': 99999999,
            'is_admin': True
        }
        save_users(users)

@app.before_first_request
def before_first_request():
    init_users()  # Ensure users data is initialized before the first request

@app.route('/')
def home():
    username = session.get('username')
    if username:
        users = load_users()
        user = users.get(username)
        if user:
            return render_template('index.html', page='home', page_title="Home", username=user['password'], tokens=user['tokens'], is_admin=user['is_admin'])
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

        users = load_users()
        if username in users:
            flash("Username already taken!", "error")
            return redirect(url_for('signup'))

        # Add the new user to the users dictionary
        users[username] = {'password': password, 'balance': 100, 'tokens': 0, 'is_admin': False}
        save_users(users)
        
        flash("Account created successfully!", "success")
        return redirect(url_for('home'))

    return render_template('index.html', page='signup', page_title="Sign Up")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect(url_for('login'))

        users = load_users()
        user = users.get(username)

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
        from_user = session.get('username')
        to_user = request.form['to_user']
        amount = int(request.form['amount'])

        if not from_user or not to_user or amount <= 0:
            flash("All fields are required, and the amount must be greater than 0!", "error")
            return redirect(url_for('transfer'))

        users = load_users()

        if from_user not in users or to_user not in users:
            flash("One or both users not found!", "error")
            return redirect(url_for('transfer'))

        from_user_data = users[from_user]
        to_user_data = users[to_user]

        # Regular users can only transfer their own tokens
        if from_user_data['tokens'] < amount and not from_user_data['is_admin']:  # Admin has infinite tokens
            flash(f"{from_user} does not have enough tokens!", "error")
            return redirect(url_for('transfer'))

        # Proceed with the transfer
        if not from_user_data['is_admin']:  # Admin is not included in this check
            from_user_data['tokens'] -= amount
        to_user_data['tokens'] += amount

        save_users(users)
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
        
        users = load_users()

        if action == 'reset_password':
            new_password = request.form.get('new_password')
            if not new_password:
                flash("New password is required.", "error")
                return redirect(url_for('admin'))

            if username in users:
                users[username]['password'] = new_password
                save_users(users)
                flash(f"Password for {username} has been reset.", "success")
            else:
                flash(f"User {username} not found.", "error")

        elif action == 'reset_tokens':
            if username in users:
                users[username]['tokens'] = 0
                save_users(users)
                flash(f"Tokens for {username} have been reset.", "success")
            else:
                flash(f"User {username} not found.", "error")

        elif action == 'delete_db':
            confirm = request.form.get('confirm')
            if confirm == 'yes':
                os.remove(USERS_FILE)
                flash("User data deleted successfully. You will need to recreate the app.", "info")
                return redirect(url_for('home'))

        save_users(users)

    return render_template('index.html', page='admin', page_title="Admin Controls")


# Route to export user data as JSON
@app.route('/export_data', methods=['GET'])
def export_data():
    users = load_users()
    # Exporting the user data as a JSON file for download
    response = jsonify(users)
    response.headers['Content-Disposition'] = 'attachment; filename=users_data.json'
    return response


# Route to load existing JSON data into the app
@app.route('/load_data', methods=['POST'])
def load_data():
    if 'file' not in request.files:
        flash("No file part", "error")
        return redirect(url_for('home'))

    file = request.files['file']
    if file.filename == '':
        flash("No selected file", "error")
        return redirect(url_for('home'))

    try:
        data = json.load(file)
        save_users(data)
        flash("User data loaded successfully.", "success")
    except Exception as e:
        flash(f"Error loading file: {e}", "error")

    return redirect(url_for('home'))


if __name__ == "__main__":
    # Initialize users data before starting the application
    init_users()
    app.run(debug=True)
