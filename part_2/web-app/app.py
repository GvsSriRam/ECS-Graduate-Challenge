# import os
# import sqlite3
# import json
# import random
# import smtplib
# from email.mime.text import MIMEText
# from io import StringIO, BytesIO
# import csv

# from flask import Flask, g, request, redirect, url_for, session, flash, send_file, render_template_string
# from flask_mail import Mail, Message

# # ===============================
# # Configuration and Initialization
# # ===============================
# app = Flask(__name__)
# app.secret_key = 'your-secret-key-here'  # Replace with a secure random key in production
# DATABASE = 'app.db'

# def get_db():
#     db = getattr(g, '_database', None)
#     if db is None:
#         db = g._database = sqlite3.connect(DATABASE)
#         db.row_factory = sqlite3.Row
#     return db

# @app.teardown_appcontext
# def close_connection(exception):
#     db = getattr(g, '_database', None)
#     if db is not None:
#         db.close()

# def init_db():
#     """Initialize the database with judges and scores tables."""
#     with app.app_context():
#         db = get_db()
#         db.execute('''
#             CREATE TABLE IF NOT EXISTS judges (
#                 email TEXT PRIMARY KEY,
#                 name TEXT NOT NULL,
#                 pin TEXT,
#                 assigned_posters TEXT  -- Stored as JSON list of poster IDs
#             )
#         ''')
#         db.execute('''
#             CREATE TABLE IF NOT EXISTS scores (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 judge_email TEXT,
#                 poster_id TEXT,
#                 score INTEGER,
#                 UNIQUE(judge_email, poster_id)
#             )
#         ''')
#         db.commit()

# # Initialize DB on first run
# if not os.path.exists(DATABASE):
#     init_db()
#     # Insert sample judge data for demo purposes
#     db = sqlite3.connect(DATABASE)
#     sample_judges = [
#         ("judge1@example.com", "Judge One", json.dumps(["poster1", "poster2", "poster3"])),
#         ("judge2@example.com", "Judge Two", json.dumps(["poster2", "poster4"]))
#     ]
#     db.executemany("INSERT OR IGNORE INTO judges (email, name, assigned_posters) VALUES (?, ?, ?)", sample_judges)
#     db.commit()
#     db.close()

# # In-memory OTP store: mapping email -> OTP (for a 24-hour hackathon prototype, this is acceptable)
# otp_store = {}

# # ===============================
# # Flask-Mail Configuration
# # ===============================
# app.config.update(
#     MAIL_SERVER='smtp.gmail.com',
#     MAIL_PORT=587,
#     MAIL_USE_TLS=True,
#     MAIL_USERNAME='your_email@gmail.com',        # Replace with your email address
#     MAIL_PASSWORD='your_app_password',             # Replace with your app-specific password
#     MAIL_DEFAULT_SENDER='your_email@gmail.com'
# )

# mail = Mail(app)

# def send_otp(email, otp):
#     """
#     Sends an OTP email using Flask-Mail.
#     """
#     msg = Message("Your Login OTP", recipients=[email])
#     msg.body = f"Your OTP for login is: {otp}"
#     try:
#         mail.send(msg)
#         print(f"Sent OTP to {email}")
#     except Exception as e:
#         print(f"Error sending email: {e}")

# # ===============================
# # Root Route for Easy Navigation
# # ===============================
# @app.route('/')
# def index():
#     """Redirect to dashboard if logged in, else to login page."""
#     if 'user' in session:
#         return redirect(url_for('dashboard'))
#     else:
#         return redirect(url_for('login'))

# # ===============================
# # Routes for Authentication
# # ===============================
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     """Judge enters their email to receive an OTP."""
#     if request.method == 'POST':
#         email = request.form.get('email')
#         db = get_db()
#         cur = db.execute("SELECT * FROM judges WHERE email = ?", (email,))
#         judge = cur.fetchone()
#         if judge:
#             # Generate a 6-digit OTP and store it
#             otp = str(random.randint(100000, 999999))
#             otp_store[email] = otp
#             send_otp(email, otp)
#             session['pending_email'] = email
#             flash("An OTP has been sent to your email. Please enter it below.")
#             return redirect(url_for('verify'))
#         else:
#             flash("Email not authorized.")
#             return redirect(url_for('login'))
#     # Simple HTML for login
#     return render_template_string('''
#         <h2>Judge Login</h2>
#         <form method="post">
#             Email: <input type="email" name="email" required>
#             <input type="submit" value="Send OTP">
#         </form>
#     ''')

# @app.route('/verify', methods=['GET', 'POST'])
# def verify():
#     """Judge enters the OTP received via email."""
#     pending_email = session.get('pending_email')
#     if not pending_email:
#         return redirect(url_for('login'))
#     if request.method == 'POST':
#         otp_input = request.form.get('otp')
#         if otp_store.get(pending_email) == otp_input:
#             # OTP is correct; log the judge in
#             session['user'] = pending_email
#             otp_store.pop(pending_email, None)
#             flash("Logged in successfully.")
#             return redirect(url_for('dashboard'))
#         else:
#             flash("Invalid OTP. Please try again.")
#             return redirect(url_for('verify'))
#     return render_template_string('''
#         <h2>Enter OTP</h2>
#         <form method="post">
#             OTP: <input type="text" name="otp" required>
#             <input type="submit" value="Verify">
#         </form>
#     ''')

# @app.route('/logout')
# def logout():
#     session.clear()
#     flash("Logged out.")
#     return redirect(url_for('login'))

# # ===============================
# # Judge Dashboard and Scoring
# # ===============================
# @app.route('/dashboard')
# def dashboard():
#     """Display assigned posters and current scores for the logged-in judge."""
#     if 'user' not in session:
#         return redirect(url_for('login'))
#     email = session['user']
#     db = get_db()
#     cur = db.execute("SELECT * FROM judges WHERE email = ?", (email,))
#     judge = cur.fetchone()
#     if not judge:
#         flash("Judge not found.")
#         return redirect(url_for('login'))
#     # Load assigned posters (stored as a JSON list)
#     assigned_posters = json.loads(judge['assigned_posters']) if judge['assigned_posters'] else []
#     # Retrieve existing scores for these posters
#     scores = {}
#     for poster in assigned_posters:
#         cur = db.execute("SELECT score FROM scores WHERE judge_email = ? AND poster_id = ?", (email, poster))
#         row = cur.fetchone()
#         scores[poster] = row['score'] if row else None
#     # Render a simple dashboard (each judge sees only their own scores)
#     dashboard_html = f"<h2>Welcome, {judge['name']}!</h2>"
#     dashboard_html += "<h3>Your Assigned Posters:</h3><ul>"
#     for poster in assigned_posters:
#         score = scores[poster]
#         dashboard_html += f"<li>{poster} - Score: {score if score is not None else 'Not Scored'} " \
#                           f'<a href="{url_for("score", poster_id=poster)}">Enter/Update Score</a></li>'
#     dashboard_html += "</ul>"
#     dashboard_html += '<br><a href="/logout">Logout</a>'
#     return dashboard_html

# @app.route('/score/<poster_id>', methods=['GET', 'POST'])
# def score(poster_id):
#     """Allow a judge to enter or update a score for an assigned poster.
#     If a score exists, pre-fill the input field with the current value."""
#     if 'user' not in session:
#         return redirect(url_for('login'))
#     email = session['user']
#     db = get_db()
#     cur = db.execute("SELECT assigned_posters FROM judges WHERE email = ?", (email,))
#     row = cur.fetchone()
#     if not row:
#         flash("Judge not found.")
#         return redirect(url_for('login'))
#     assigned_posters = json.loads(row['assigned_posters']) if row['assigned_posters'] else []
#     if poster_id not in assigned_posters:
#         flash("You are not assigned to this poster.")
#         return redirect(url_for('dashboard'))
    
#     # Get the current score if it exists
#     cur = db.execute("SELECT score FROM scores WHERE judge_email = ? AND poster_id = ?", (email, poster_id))
#     row = cur.fetchone()
#     current_score = row['score'] if row else ""
    
#     if request.method == 'POST':
#         score_val = request.form.get('score')
#         try:
#             score_int = int(score_val)
#             if score_int < 0 or score_int > 10:
#                 flash("Score must be between 0 and 10.")
#                 return redirect(url_for('score', poster_id=poster_id))
#         except ValueError:
#             flash("Invalid score.")
#             return redirect(url_for('score', poster_id=poster_id))
#         # Insert or update the score in the database
#         db.execute('''INSERT INTO scores (judge_email, poster_id, score)
#                       VALUES (?, ?, ?)
#                       ON CONFLICT(judge_email, poster_id) DO UPDATE SET score = ?''',
#                    (email, poster_id, score_int, score_int))
#         db.commit()
#         flash("Score updated.")
#         return redirect(url_for('dashboard'))
    
#     return render_template_string('''
#         <h2>Enter Score for {{ poster_id }}</h2>
#         <form method="post">
#             Score (0-10): 
#             <input type="number" name="score" min="0" max="10" value="{{ current_score }}" required>
#             <input type="submit" value="Submit">
#         </form>
#         <br><a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
#     ''', poster_id=poster_id, current_score=current_score)

# # ===============================
# # Admin Export Endpoint
# # ===============================
# @app.route('/export')
# def export():
#     """
#     Exports the complete scores as a CSV.
#     For demo purposes, access is protected by a simple key in the URL (e.g., /export?key=adminsecret).
#     """
#     key = request.args.get('key')
#     if key != 'adminsecret':  # Replace with a secure method in production
#         return "Unauthorized", 401
#     db = get_db()
#     cur = db.execute("SELECT * FROM scores")
#     rows = cur.fetchall()
#     output = StringIO()
#     writer = csv.writer(output)
#     writer.writerow(["judge_email", "poster_id", "score"])
#     for row in rows:
#         writer.writerow([row['judge_email'], row['poster_id'], row['score']])
#     output.seek(0)
#     return send_file(BytesIO(output.getvalue().encode()),
#                      mimetype='text/csv',
#                      as_attachment=True,
#                      attachment_filename='scores.csv')

# # ===============================
# # Run the Application
# # ===============================
# if __name__ == '__main__':
#     app.run(debug=True)


import os
import sqlite3
import json
import random
import smtplib
from email.mime.text import MIMEText
from io import StringIO, BytesIO
import csv

from flask import Flask, g, request, redirect, url_for, session, flash, send_file, render_template_string
from flask_mail import Mail, Message

# ===============================
# Configuration and Initialization
# ===============================
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Replace with a secure random key in production
DATABASE = 'app.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database with judges, scores, and score_changes tables."""
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS judges (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                pin TEXT,
                assigned_posters TEXT  -- Stored as JSON list of poster IDs
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                judge_email TEXT,
                poster_id TEXT,
                score INTEGER,
                UNIQUE(judge_email, poster_id)
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS score_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                judge_email TEXT,
                poster_id TEXT,
                old_score INTEGER,
                new_score INTEGER,
                change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

# Initialize DB on first run
if not os.path.exists(DATABASE):
    init_db()
    # Insert sample judge data for demo purposes
    db = sqlite3.connect(DATABASE)
    sample_judges = [
        ("judge1@example.com", "Judge One", json.dumps(["poster1", "poster2", "poster3"])),
        ("judge2@example.com", "Judge Two", json.dumps(["poster2", "poster4"]))
    ]
    db.executemany("INSERT OR IGNORE INTO judges (email, name, assigned_posters) VALUES (?, ?, ?)", sample_judges)
    db.commit()
    db.close()

# In-memory OTP store: mapping email -> OTP (for a 24-hour hackathon prototype, this is acceptable)
otp_store = {}

# ===============================
# Flask-Mail Configuration
# ===============================
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='rajmohan8081@gmail.com',        # Replace with your email address
    MAIL_PASSWORD='ygxc olrd xjhm gawf',             # Replace with your app-specific password
    MAIL_DEFAULT_SENDER='rajmohan8081@gmail.com'
)

mail = Mail(app)

def send_otp(email, otp):
    """
    Sends an OTP email using Flask-Mail.
    """
    msg = Message("Your Login OTP", recipients=[email])
    msg.body = f"Your OTP for login is: {otp}"
    try:
        mail.send(msg)
        print(f"Sent OTP to {email}")
    except Exception as e:
        print(f"Error sending email: {e}")

# ===============================
# Root Route for Easy Navigation
# ===============================
@app.route('/')
def index():
    """Redirect to dashboard if logged in, else to login page."""
    if 'user' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

# ===============================
# Routes for Authentication
# ===============================
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     """Judge enters their email to receive an OTP."""
#     if request.method == 'POST':
#         email = request.form.get('email')
#         db = get_db()
#         cur = db.execute("SELECT * FROM judges WHERE email = ?", (email,))
#         judge = cur.fetchone()
#         if judge:
#             # Generate a 6-digit OTP and store it
#             otp = str(random.randint(100000, 999999))
#             otp_store[email] = otp
#             send_otp(email, otp)
#             session['pending_email'] = email
#             flash("An OTP has been sent to your email. Please enter it below.")
#             return redirect(url_for('verify'))
#         else:
#             flash("Email not authorized.")
#             return redirect(url_for('login'))
#     # Simple HTML for login
#     return render_template_string('''
#         <h2>Judge Login</h2>
#         <form method="post">
#             Email: <input type="email" name="email" required>
#             <input type="submit" value="Send OTP">
#         </form>
#     ''')

# @app.route('/verify', methods=['GET', 'POST'])
# def verify():
#     """Judge enters the OTP received via email."""
#     pending_email = session.get('pending_email')
#     if not pending_email:
#         return redirect(url_for('login'))
#     if request.method == 'POST':
#         otp_input = request.form.get('otp')
#         if otp_store.get(pending_email) == otp_input:
#             # OTP is correct; log the judge in
#             session['user'] = pending_email
#             otp_store.pop(pending_email, None)
#             flash("Logged in successfully.")
#             return redirect(url_for('dashboard'))
#         else:
#             flash("Invalid OTP. Please try again.")
#             return redirect(url_for('verify'))
#     return render_template_string('''
#         <h2>Enter OTP</h2>
#         <form method="post">
#             OTP: <input type="text" name="otp" required>
#             <input type="submit" value="Verify">
#         </form>
#     ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Dark-themed login screen similar in style to the dashboard.
    Instead of a phone number, we keep the email-based login logic.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        db = get_db()
        cur = db.execute("SELECT * FROM judges WHERE email = ?", (email,))
        judge = cur.fetchone()
        if judge:
            # Generate a 6-digit OTP and store it
            otp = str(random.randint(100000, 999999))
            otp_store[email] = otp
            send_otp(email, otp)
            session['pending_email'] = email
            flash("An OTP has been sent to your email. Please enter it below.")
            return redirect(url_for('verify'))
        else:
            flash("Email not authorized.")
            return redirect(url_for('login'))

    # Render a dark-themed login page
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Login</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <!-- IBM Plex Sans via Google Fonts -->
  <link rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap"/>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'IBM Plex Sans', sans-serif;
    }
    body {
      background-color: #121212;
      color: #fff;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }
    .card {
      background-color: #1f1f1f;
      border-radius: 20px;
      width: 90%;
      max-width: 400px;
      padding: 2rem;
    }
    .title {
      font-size: 1.5rem;
      font-weight: 600;
      margin-bottom: 1.5rem;
      text-align: center;
    }
    .input-group {
      margin-bottom: 1rem;
    }
    label {
      display: block;
      font-size: 0.9rem;
      margin-bottom: 0.4rem;
      color: #ccc;
    }
    input[type="email"] {
      width: 100%;
      padding: 0.8rem;
      border-radius: 10px;
      border: none;
      outline: none;
      font-size: 1rem;
      background-color: #2a2a2a;
      color: #fff;
    }
    .btn {
      display: block;
      width: 100%;
      background-color: #4285F4;
      color: #fff;
      font-size: 1rem;
      font-weight: 600;
      text-align: center;
      padding: 0.8rem;
      border: none;
      border-radius: 10px;
      margin-top: 1rem;
      cursor: pointer;
    }
    .btn:hover {
      background-color: #357ae8;
    }
    .info {
      font-size: 0.85rem;
      color: #aaa;
      margin-top: 0.5rem;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="title">Hi! Welcome</div>
    <form method="post">
      <div class="input-group">
        <label for="email">Enter your email</label>
        <input type="email" id="email" name="email" placeholder="your.email@example.com" required />
      </div>
      <button type="submit" class="btn">Send OTP</button>
      <div class="info">Build for Syracuse University 🍊</div>
    </form>
  </div>
</body>
</html>
    ''')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    """
    Dark-themed verify screen with 6 separate OTP inputs.
    Automatically moves cursor from one box to the next, 
    and opens the number pad on mobile.
    """
    pending_email = session.get('pending_email')
    if not pending_email:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Merge the 6 digits into one string
        otp_input = (
            request.form.get('otp1', '') +
            request.form.get('otp2', '') +
            request.form.get('otp3', '') +
            request.form.get('otp4', '') +
            request.form.get('otp5', '') +
            request.form.get('otp6', '')
        )
        
        if otp_store.get(pending_email) == otp_input:
            # OTP is correct; log the judge in
            session['user'] = pending_email
            otp_store.pop(pending_email, None)
            flash("Logged in successfully.")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid OTP. Please try again.")
            return redirect(url_for('verify'))

    # Render the 6-digit OTP form
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Verify OTP</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <!-- IBM Plex Sans via Google Fonts (or any other) -->
  <link rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap"/>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'IBM Plex Sans', sans-serif;
    }
    body {
      background-color: #121212;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
    }
    .card {
      background-color: #1f1f1f;
      padding: 2rem;
      border-radius: 16px;
      width: 90%;
      max-width: 400px;
      text-align: center;
    }
    .card h2 {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
    }
    .card p {
      color: #bbb;
      margin-bottom: 1.5rem;
    }
    form {
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .otp-container {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }
    .otp-input {
      width: 3rem;
      height: 3rem;
      font-size: 1.5rem;
      text-align: center;
      border-radius: 8px;
      border: none;
      background-color: #2a2a2a;
      color: #fff;
    }
    .submit-btn {
      background-color: #4285F4;
      color: #fff;
      font-size: 1rem;
      padding: 0.8rem 1.5rem;
      border: none;
      border-radius: 8px;
      cursor: pointer;
    }
    .submit-btn:hover {
      background-color: #357ae8;
    }
    .resend-link {
      margin-top: 1rem;
      color: #4285F4;
      text-decoration: underline;
      cursor: pointer;
      font-size: 0.9rem;
    }
  </style>
</head>
<body>
  <div class="card">
    <h2>Verify OTP</h2>
    <p>Code has been sent to {{ pending_email }}</p>
    <form method="post" id="otpForm">
      <div class="otp-container">
        <!-- 6 separate inputs, each 1 digit -->
        {% for i in range(1,7) %}
        <input
          type="tel"
          inputmode="numeric"
          maxlength="1"
          class="otp-input"
          name="otp{{ i }}"
          id="otp{{ i }}"
          required
        />
        {% endfor %}
      </div>
      <button type="submit" class="submit-btn">Verify</button>
    </form>
    <div 
      class="resend-link" 
      onclick="window.location.href='/login';">
      Didn’t get OTP? Resend Code
    </div>
  </div>

  <script>
    // Focus the first input on load
    document.getElementById('otp1').focus();

    // For all 6 inputs, jump to next on keyup if a single digit is entered
    const inputs = document.querySelectorAll('.otp-input');
    inputs.forEach((input, index) => {
      input.addEventListener('input', (e) => {
        if (input.value.length === 1) {
          // Move to next input if it exists
          if (index < inputs.length - 1) {
            inputs[index + 1].focus();
          }
        }
      });

      // Handle backspace to move focus back
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && input.value === '' && index > 0) {
          inputs[index - 1].focus();
        }
      });
    });
  </script>
</body>
</html>
    ''', pending_email=pending_email)



@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for('login'))

# ===============================
# Judge Dashboard and Scoring
# ===============================
# @app.route('/dashboard')
# def dashboard():
#     """Display assigned posters and current scores for the logged-in judge."""
#     if 'user' not in session:
#         return redirect(url_for('login'))
#     email = session['user']
#     db = get_db()
#     cur = db.execute("SELECT * FROM judges WHERE email = ?", (email,))
#     judge = cur.fetchone()
#     if not judge:
#         flash("Judge not found.")
#         return redirect(url_for('login'))
#     # Load assigned posters (stored as a JSON list)
#     assigned_posters = json.loads(judge['assigned_posters']) if judge['assigned_posters'] else []
#     # Retrieve existing scores for these posters
#     scores = {}
#     for poster in assigned_posters:
#         cur = db.execute("SELECT score FROM scores WHERE judge_email = ? AND poster_id = ?", (email, poster))
#         row = cur.fetchone()
#         scores[poster] = row['score'] if row else None
#     # Render a simple dashboard (each judge sees only their own scores)
#     dashboard_html = f"<h2>Welcome, {judge['name']}!</h2>"
#     dashboard_html += "<h3>Your Assigned Posters:</h3><ul>"
#     for poster in assigned_posters:
#         score = scores[poster]
#         dashboard_html += f"<li>{poster} - Score: {score if score is not None else 'Not Scored'} " \
#                           f'<a href="{url_for("score", poster_id=poster)}">Enter/Update Score</a></li>'
#     dashboard_html += "</ul>"
#     dashboard_html += '<br><a href="/score_log">View Your Score Change Log</a>'
#     dashboard_html += '<br><a href="/logout">Logout</a>'
#     return dashboard_html
# SECOND TYPE: dashboard
# @app.route('/dashboard')
# def dashboard():
#     """
#     Display assigned posters in a UI inspired by the referenced design:
#     - A vertical list where each assigned poster looks like a "room" item.
#     - Shows poster ID, current score, and links to set/update that score.
#     """
#     if 'user' not in session:
#         return redirect(url_for('login'))
    
#     email = session['user']
#     db = get_db()
#     cur = db.execute("SELECT * FROM judges WHERE email = ?", (email,))
#     judge = cur.fetchone()
#     if not judge:
#         flash("Judge not found.")
#         return redirect(url_for('login'))
    
#     # Load assigned posters (stored as a JSON list in the DB)
#     assigned_posters = json.loads(judge['assigned_posters']) if judge['assigned_posters'] else []
    
#     # Retrieve existing scores for these posters
#     scores = {}
#     for poster in assigned_posters:
#         cur = db.execute("SELECT score FROM scores WHERE judge_email = ? AND poster_id = ?", (email, poster))
#         row = cur.fetchone()
#         scores[poster] = row['score'] if row else None
    
#     # Render a dashboard UI similar to your reference image
#     dashboard_html = render_template_string('''
# <!DOCTYPE html>
# <html lang="en">
# <head>
#   <meta charset="UTF-8" />
#   <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
#   <title>Dashboard</title>
#   <!-- You can use a simple reset or bootstrap, but here is minimal styling -->
#   <style>
#     body {
#       margin: 0;
#       padding: 0;
#       font-family: sans-serif;
#       background: #f7f7f7; /* or use a gradient if you want */
#     }
#     .top-bar {
#       display: flex;
#       align-items: center;
#       justify-content: center;
#       background: #f7f7f7;
#       padding: 1rem;
#       border-bottom: 1px solid #ddd;
#     }
#     .top-bar h1 {
#       margin: 0;
#       font-size: 1.4rem;
#     }
#     .rooms-container {
#       max-width: 450px;
#       margin: 1rem auto;
#       border-radius: 16px;
#       overflow: hidden;
#     }
#     .room-list {
#       list-style: none;
#       margin: 0;
#       padding: 0;
#     }
#     .room-item {
#       display: flex;
#       align-items: center;
#       justify-content: space-between;
#       background: #fff;
#       padding: 1rem;
#       border-bottom: 1px solid #eee;
#       text-decoration: none;
#       color: #000;
#     }
#     .room-item:last-child {
#       border-bottom: none;
#     }
#     .icon-circle {
#       min-width: 40px;
#       min-height: 40px;
#       border-radius: 50%;
#       background: #eee;
#       display: flex;
#       align-items: center;
#       justify-content: center;
#       margin-right: 1rem;
#     }
#     .room-label {
#       display: flex;
#       flex-direction: column;
#       flex: 1;
#     }
#     .room-label span:first-child {
#       font-weight: 600;
#       margin-bottom: 4px;
#     }
#     .score-link {
#       font-size: 0.9rem;
#       color: #4285F4;
#       text-decoration: underline;
#     }
#     .bottom-links {
#       text-align: center;
#       margin-top: 1rem;
#     }
#     .bottom-links a {
#       display: inline-block;
#       padding: 0.6rem 1rem;
#       margin: 0.2rem;
#       border: none;
#       background: #4285F4;
#       color: #fff;
#       border-radius: 8px;
#       text-decoration: none;
#     }
#     .bottom-links a:hover {
#       background: #357ae8;
#     }
#   </style>
# </head>
# <body>
#   <div class="top-bar">
#     <h1>Welcome, {{ judge_name }}!</h1>
#   </div>
  
#   <div class="rooms-container">
#     <ul class="room-list">
#       {% for poster in assigned_posters %}
#       <li class="room-item">
#         <div class="icon-circle">
#           <!-- Any icon or emoji you like, e.g. a "poster" icon or a default couch icon -->
#           🏷️
#         </div>
#         <div class="room-label">
#           <span>{{ poster }}</span>
#           <span>
#             Score: 
#             {% if scores[poster] is not none %}
#               {{ scores[poster] }}
#             {% else %}
#               Not Scored
#             {% endif %}
#           </span>
#         </div>
#         <a class="score-link" href="{{ url_for('score', poster_id=poster) }}">
#           Update
#         </a>
#       </li>
#       {% endfor %}
#     </ul>
#   </div>
  
#   <div class="bottom-links">
#     <a href="{{ url_for('score_log') }}">Score Log</a>
#     <a href="{{ url_for('logout') }}">Logout</a>
#   </div>
# </body>
# </html>
#     ''', 
#     judge_name=judge['name'],
#     assigned_posters=assigned_posters,
#     scores=scores)
    
#     return dashboard_html

@app.route('/dashboard')
def dashboard():
    """
    Dark-theme dashboard with a rounded top header that greets the user,
    shows notifications/profile, and lists assigned posters in a card-like format,
    using IBM Plex Sans for all text.
    """
    if 'user' not in session:
        return redirect(url_for('login'))
    
    email = session['user']
    db = get_db()
    cur = db.execute("SELECT * FROM judges WHERE email = ?", (email,))
    judge = cur.fetchone()
    if not judge:
        flash("Judge not found.")
        return redirect(url_for('login'))
    
    assigned_posters = json.loads(judge['assigned_posters']) if judge['assigned_posters'] else []
    
    # Retrieve existing scores for these posters
    scores = {}
    for poster in assigned_posters:
        cur = db.execute(
            "SELECT score FROM scores WHERE judge_email = ? AND poster_id = ?",
            (email, poster)
        )
        row = cur.fetchone()
        scores[poster] = row['score'] if row else None

    # Render a dark-themed dashboard with IBM Plex Sans
    dashboard_html = render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Dashboard</title>
  <!-- Include IBM Plex Sans via Google Fonts -->
  <link rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap"/>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'IBM Plex Sans', sans-serif;
    }
    body {
      background-color: #121212;
      color: #fff;
    }
    .header {
      background-color: #1f1f1f;
      border-bottom-left-radius: 24px;
      border-bottom-right-radius: 24px;
      padding: 2rem 1.5rem;
    }
    .header .top-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .header .greeting h2 {
      font-size: 1.2rem;
      font-weight: 600;
      margin-bottom: 0.2rem;
    }
    .header .greeting span {
      font-size: 0.9rem;
      color: #ccc;
    }
    .icon-row {
      display: flex;
      gap: 1rem;
      align-items: center;
    }
    .icon-row .icon-circle {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: #2a2a2a;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    }
    .icon-row .profile-pic img {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      object-fit: cover;
    }
    .main-content {
      margin-top: 1rem;
      padding: 1.5rem;
    }
    .poster-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .poster-card {
      background-color: #1f1f1f;
      border-radius: 12px;
      padding: 1rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .poster-info {
      display: flex;
      flex-direction: column;
    }
    .poster-name {
      font-weight: 600;
      margin-bottom: 0.3rem;
    }
    .poster-score {
      color: #999;
      font-size: 0.9rem;
    }
    .score-link {
      color: #fff;
      background-color: #4285F4;
      padding: 0.4rem 0.6rem;
      border-radius: 8px;
      text-decoration: none;
      font-size: 0.85rem;
    }
    .score-link:hover {
      background-color: #357ae8;
    }
    .bottom-links {
      display: flex;
      justify-content: space-around;
      margin-top: 2rem;
    }
    .bottom-links a {
      text-decoration: none;
      color: #fff;
      background: #4285F4;
      padding: 0.6rem 1.2rem;
      border-radius: 8px;
      transition: background 0.2s ease-in-out;
    }
    .bottom-links a:hover {
      background: #357ae8;
    }
    # .top-row {
    #   display: flex;
    #   justify-content: space-around;
    #   margin-top: 2rem;
    # }
    .top-row a {
      text-decoration: none;
      color: #fff;
      background: red;
      padding: 0.6rem 1.2rem;
      border-radius: 8px;
      transition: background 0.2s ease-in-out;
    }
    # .top-row a:hover {
    #   background: #444;
    # }
  </style>
</head>
<body>
  <!-- Header -->
  <div class="header">
    <div class="top-row">
      <div class="greeting">
        <h2>Hi &#128075; {{ judge_name }}!</h2>
        <span>Welcome back</span>
      </div>
      <div class="top-row">
        <!-- Notification icon -->
        
        <!-- Profile pic circle -->
        <a href="{{ url_for('logout') }}">Logout</a>
      </div>
    </div>
  </div>

  <!-- Main content -->
  <div class="main-content">
    <div class="poster-list">
      {% for poster in assigned_posters %}
      <div class="poster-card">
        <div class="poster-info">
          <span class="poster-name">{{ poster }}</span>
          {% if scores[poster] is not none %}
            <span class="poster-score">Score: {{ scores[poster] }}</span>
          {% else %}
            <span class="poster-score">Not Scored</span>
          {% endif %}
        </div>
        <a class="score-link" href="{{ url_for('score', poster_id=poster) }}">
          Update
        </a>
      </div>
      {% endfor %}
    </div>

    <div class="bottom-links">
      <a href="{{ url_for('score_log') }}">Score Log</a>
      
    </div>
  </div>
</body>
</html>
    ''',
    judge_name=judge['name'],
    assigned_posters=assigned_posters,
    scores=scores
    )
    
    return dashboard_html

# @app.route('/score/<poster_id>', methods=['GET', 'POST'])
# def score(poster_id):
#     """
#     Dark-themed /score screen inspired by the provided screenshot:
#      - A centered card with "Enter Score"
#      - Poster ID
#      - Input for 0–10
#      - Large Submit button
#      - 'Back to Dashboard' link
#     """
#     if 'user' not in session:
#         return redirect(url_for('login'))
#     email = session['user']

#     db = get_db()
#     cur = db.execute("SELECT assigned_posters FROM judges WHERE email = ?", (email,))
#     row = cur.fetchone()
#     if not row:
#         flash("Judge not found.")
#         return redirect(url_for('login'))

#     assigned_posters = json.loads(row['assigned_posters']) if row['assigned_posters'] else []
#     if poster_id not in assigned_posters:
#         flash("You are not assigned to this poster.")
#         return redirect(url_for('dashboard'))

#     # Retrieve current score, if any
#     cur = db.execute("SELECT score FROM scores WHERE judge_email = ? AND poster_id = ?",
#                      (email, poster_id))
#     existing_row = cur.fetchone()
#     current_score = existing_row['score'] if existing_row else ""

#     if request.method == 'POST':
#         score_val = request.form.get('score')
#         try:
#             score_int = int(score_val)
#             if score_int < 0 or score_int > 10:
#                 flash("Score must be between 0 and 10.")
#                 return redirect(url_for('score', poster_id=poster_id))
#         except ValueError:
#             flash("Invalid score.")
#             return redirect(url_for('score', poster_id=poster_id))

#         # Insert or update the score
#         cur = db.execute("SELECT score FROM scores WHERE judge_email = ? AND poster_id = ?",
#                          (email, poster_id))
#         row = cur.fetchone()
#         old_score = row['score'] if row else None

#         db.execute('''
#             INSERT INTO scores (judge_email, poster_id, score)
#             VALUES (?, ?, ?)
#             ON CONFLICT(judge_email, poster_id) DO UPDATE SET score = ?
#         ''', (email, poster_id, score_int, score_int))
#         db.commit()

#         # Log changes (if needed)
#         if old_score is None or old_score != score_int:
#             db.execute('''
#                 INSERT INTO score_changes (judge_email, poster_id, old_score, new_score)
#                 VALUES (?, ?, ?, ?)
#             ''', (email, poster_id, old_score, score_int))
#             db.commit()

#         flash("Score updated.")
#         return redirect(url_for('dashboard'))

#     # Render the new, dark-themed "Enter Score" card
#     return render_template_string('''
# <!DOCTYPE html>
# <html lang="en">
# <head>
#   <meta charset="UTF-8"/>
#   <title>Enter Score</title>
#   <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
#   <!-- IBM Plex Sans (matching your dashboard) -->
#   <link rel="stylesheet"
#         href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
#   <style>
#     * {
#       box-sizing: border-box;
#       margin: 0;
#       padding: 0;
#       font-family: 'IBM Plex Sans', sans-serif;
#     }
#     body {
#       background-color: #121212;
#       color: #fff;
#       display: flex;
#       align-items: center;
#       justify-content: center;
#       height: 100vh;
#     }
#     .card {
#       background-color: #1f1f1f;
#       width: 90%;
#       max-width: 320px;
#       border-radius: 12px;
#       padding: 2rem;
#       text-align: center;
#       box-shadow: 0 2px 5px rgba(0,0,0,0.3);
#     }
#     .card h1 {
#       font-size: 1.4rem;
#       margin-bottom: 1rem;
#     }
#     .poster-id {
#       font-size: 1rem;
#       color: #ccc;
#       margin-bottom: 1.5rem;
#     }
#     .score-label {
#       font-size: 0.9rem;
#       color: #666;
#     }
#     .score-input {
#       font-size: 2rem;
#       margin: 0.5rem 0 1rem 0;
#       border: none;
#       border-radius: 8px;
#       width: 6rem;
#       text-align: center;
#       background-color: #2a2a2a;
#       color: #fff;
#       outline: none;
#     }
#     .submit-btn {
#       background-color: #4285F4;
#       color: #fff;
#       font-size: 1rem;
#       font-weight: 600;
#       padding: 0.8rem 0;
#       border: none;
#       border-radius: 8px;
#       width: 100%;
#       max-width: 200px;
#       margin: 0 auto;
#       display: block;
#       cursor: pointer;
#     }
#     .submit-btn:hover {
#       background-color: #357ae8;
#     }
#     .back-link {
#       display: block;
#       margin-top: 1rem;
#       font-size: 0.9rem;
#       color: #4285F4;
#       text-decoration: underline;
#     }
#     .back-link:hover {
#       text-decoration: none;
#     }
#   </style>
# </head>
# <body>
#   <div class="card">
#     <h1>Enter Score</h1>
#     <div class="poster-id">{{ poster_id }}</div>

#     <form method="POST">
#       <label for="score" class="score-label">0 - 10</label>
#       <br>
#       <input 
#         type="number" 
#         name="score" 
#         id="score" 
#         class="score-input" 
#         min="0" 
#         max="10" 
#         value="{{ current_score }}" 
#         required
#       />
#       <button type="submit" class="submit-btn">Submit</button>
#     </form>
#     <a class="back-link" href="{{ url_for('dashboard') }}">Back to Dashboard</a>
#   </div>
# </body>
# </html>
#     ''', poster_id=poster_id, current_score=current_score)




@app.route('/score/<poster_id>', methods=['GET', 'POST'])
def score(poster_id):
    """Allow a judge to enter or update a score for an assigned poster.
    Pre-fills with the current score and uses a mobile-optimized UI."""
    if 'user' not in session:
        return redirect(url_for('login'))
    email = session['user']
    db = get_db()
    cur = db.execute("SELECT assigned_posters FROM judges WHERE email = ?", (email,))
    row = cur.fetchone()
    if not row:
        flash("Judge not found.")
        return redirect(url_for('login'))
    assigned_posters = json.loads(row['assigned_posters']) if row['assigned_posters'] else []
    if poster_id not in assigned_posters:
        flash("You are not assigned to this poster.")
        return redirect(url_for('dashboard'))
    
    # Get the current score if it exists
    cur = db.execute("SELECT score FROM scores WHERE judge_email = ? AND poster_id = ?", (email, poster_id))
    row = cur.fetchone()
    current_score = row['score'] if row else ""
    
    if request.method == 'POST':
        score_val = request.form.get('score')
        try:
            score_int = int(score_val)
            if score_int < 0 or score_int > 10:
                flash("Score must be between 0 and 10.")
                return redirect(url_for('score', poster_id=poster_id))
        except ValueError:
            flash("Invalid score.")
            return redirect(url_for('score', poster_id=poster_id))
        
        # Determine if there's an existing score
        cur = db.execute("SELECT score FROM scores WHERE judge_email = ? AND poster_id = ?", (email, poster_id))
        row = cur.fetchone()
        old_score = row['score'] if row else None

        # Insert or update the score
        db.execute('''INSERT INTO scores (judge_email, poster_id, score)
                      VALUES (?, ?, ?)
                      ON CONFLICT(judge_email, poster_id) DO UPDATE SET score = ?''',
                   (email, poster_id, score_int, score_int))
        db.commit()
        
        # Log the change if needed
        if old_score is None or old_score != score_int:
            db.execute('''INSERT INTO score_changes (judge_email, poster_id, old_score, new_score)
                          VALUES (?, ?, ?, ?)''', (email, poster_id, old_score, score_int))
            db.commit()
        
        flash("Score updated.")
        return redirect(url_for('dashboard'))
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Enter Score for {{ poster_id }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background-color: #121212;
      font-family: 'Roboto', sans-serif;
      color: white;
    }
    .card {
      border-radius: 20px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      background: #1f1f1f;
    }
    .score-input {
      font-size: 2rem;
      text-align: center;
      border: none;
      outline: none;
      width: 100%;
      background-color: transparent;
     color: white;
    }
    .submit-btn {
      background-color: #4285F4;
      border: none;
      color: white;
      font-size: 1.5rem;
      border-radius: 10px;
      padding: 10px 0;
      margin-top: 20px;
      width: 100%;
    }
    .submit-btn:hover {
      background-color: #357ae8;
    }
    .text-color-w{
       color: white;
    }
    .back-btn{
      padding: .5em;
      background-color: #4285F4;
      text-decoration: none;
      color: white;
      border-radius: 10px;
    }
  </style>
</head>
<body>
  <div class="container d-flex justify-content-center align-items-center vh-100">
    <div class="card p-4" style="width: 90%; max-width: 400px;">
      <h2 class="text-color-w text-center mb-4 ">Enter Score</h2>
      <h5 class=" text-center mb-4 text-color-w">{{ poster_id }}</h5>
      <form method="post">
        <div class="mb-3">
          <input type="number" name="score" min="0" max="10" value="{{ current_score }}" class="score-input" placeholder="0-10" required>
        </div>
        <button type="submit" class="submit-btn">Submit</button>
      </form>
      <a href="{{ url_for('dashboard') }}" class="btn btn-link d-block text-center mt-3 back-btn">Back</a>
    </div>
  </div>
</body>
</html>
''', poster_id=poster_id, current_score=current_score)


# ===============================
# Score Change Log for Judges
# ===============================
# @app.route('/score_log')
# def score_log():
#     """Display the log of score changes for the logged-in judge."""
#     if 'user' not in session:
#         return redirect(url_for('login'))
#     email = session['user']
#     db = get_db()
#     cur = db.execute("SELECT * FROM score_changes WHERE judge_email = ? ORDER BY change_time DESC", (email,))
#     changes = cur.fetchall()
#     log_html = "<h2>Your Score Change Log</h2>"
#     if not changes:
#         log_html += "<p>No score changes logged yet.</p>"
#     else:
#         log_html += "<table border='1' cellspacing='0' cellpadding='5'>"
#         log_html += "<tr><th>Poster ID</th><th>Old Score</th><th>New Score</th><th>Timestamp</th></tr>"
#         for change in changes:
#             log_html += f"<tr><td>{change['poster_id']}</td><td>{change['old_score']}</td><td>{change['new_score']}</td><td>{change['change_time']}</td></tr>"
#         log_html += "</table>"
#     log_html += '<br><a href="/dashboard">Back to Dashboard</a>'
#     return log_html

@app.route('/score_log')
def score_log():
    """
    Display the log of score changes as a dark-themed timeline,
    matching the style of the main dashboard screen.
    """
    if 'user' not in session:
        return redirect(url_for('login'))
    
    email = session['user']
    db = get_db()
    # Fetch changes in descending chronological order
    cur = db.execute("""
        SELECT * FROM score_changes 
        WHERE judge_email = ? 
        ORDER BY change_time DESC
    """, (email,))
    changes = cur.fetchall()

    # Render a timeline UI with dark theme and IBM Plex Sans
    log_html = render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Score Log</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!-- IBM Plex Sans -->
  <link rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'IBM Plex Sans', sans-serif;
    }
    body {
      background-color: #121212;
      color: #fff;
      padding: 1rem;
    }
    .header {
      background-color: #1f1f1f;
      border-radius: 16px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }
    .header h2 {
      font-weight: 600;
      font-size: 1.2rem;
    }
    .timeline {
      position: relative;
      margin-left: 2rem; /* space for the vertical line */
      padding: 0.5rem 0;
      border-left: 2px solid #2a2a2a; /* the timeline line */
    }
    .timeline-item {
      margin-bottom: 1.5rem;
      position: relative;
    }
    .timeline-item:last-child {
      margin-bottom: 0;
    }
    .timeline-dot {
      position: absolute;
      left: -0.53rem; /* horizontally center the dot on the line */
      top: 0.45rem;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background-color: #4285F4;
      border: 2px solid #121212; /* so it stands out from the line if needed */
    }
    .item-content {
      padding-left: 1.5rem;
    }
    .time-stamp {
      font-size: 0.85rem;
      color: #999;
      margin-bottom: 0.2rem;
    }
    .poster-id {
      font-weight: 600;
      color: #fff;
      margin-bottom: 0.2rem;
    }
    .score-change {
      font-size: 0.9rem;
      color: #ccc;
    }
    .score-change span {
      color: #76c893; /* greenish or any highlight color for new score */
    }
    .no-changes {
      font-style: italic;
      color: #ccc;
      margin-top: 2rem;
      text-align: center;
    }
    .nav-links {
      text-align: center;
      margin-top: 2rem;
    }
    .nav-links a {
      text-decoration: none;
      color: #fff;
      background: #4285F4;
      padding: 0.6rem 1.2rem;
      border-radius: 8px;
      transition: background 0.2s ease-in-out;
      margin: 0 0.5rem;
    }
    .nav-links a:hover {
      background: #357ae8;
    }
  </style>
</head>
<body>
  <div class="header">
    <h2>Your Score Change Log</h2>
  </div>

  {% if not changes %}
    <p class="no-changes">No score changes logged yet.</p>
  {% else %}
    <div class="timeline">
      {% for change in changes %}
        <div class="timeline-item">
          <div class="timeline-dot"></div>
          <div class="item-content">
            <div class="time-stamp">{{ change['change_time'] }}</div>
            <div class="poster-id">Poster: {{ change['poster_id'] }}</div>
            <div class="score-change">
              <!-- If old_score is None, it means first-time score creation -->
              {% if change['old_score'] is none %}
                Initial score set to <span>{{ change['new_score'] }}</span>
              {% else %}
                Changed from <span>{{ change['old_score'] }}</span> to <span>{{ change['new_score'] }}</span>
              {% endif %}
            </div>
          </div>
        </div>
      {% endfor %}
    </div>
  {% endif %}

  <div class="nav-links">
    <a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
    
  </div>
</body>
</html>
    ''', changes=changes)

    return log_html


# ===============================
# Admin Export Endpoint
# ===============================
@app.route('/export')
def export():
    """
    Exports the complete scores as a CSV.
    For demo purposes, access is protected by a simple key in the URL (e.g., /export?key=adminsecret).
    """
    key = request.args.get('key')
    if key != 'adminsecret':  # Replace with a secure method in production
        return "Unauthorized", 401
    db = get_db()
    cur = db.execute("SELECT * FROM scores")
    rows = cur.fetchall()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["judge_email", "poster_id", "score"])
    for row in rows:
        writer.writerow([row['judge_email'], row['poster_id'], row['score']])
    output.seek(0)
    return send_file(BytesIO(output.getvalue().encode()),
                 mimetype='text/csv',
                 as_attachment=True,
                 download_name='scores.csv')


# ===============================
# Run the Application
# ===============================
if __name__ == '__main__':
    app.run(debug=True)
