import os
import sqlite3
import json
import random
import smtplib
from email.mime.text import MIMEText
from io import StringIO, BytesIO
import csv
import openpyxl
from flask import Flask, g, request, redirect, url_for, session, flash, send_file, render_template_string
from flask_mail import Mail, Message
import qrcode

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

# def init_db():
#     """Initialize the database with judges, scores, and score_changes tables."""
#     with app.app_context():
#         db = get_db()
#         db.execute('''
#             CREATE TABLE IF NOT EXISTS judges (
#                 email TEXT PRIMARY KEY,
#                 name TEXT NOT NULL,
#                 pin TEXT,
#                 assigned_posters TEXT,  -- Stored as JSON list of poster IDs
#                 assigned_poster_titles TEXT  -- Stored as JSON object mapping poster IDs to poster titles
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
#         db.execute('''
#             CREATE TABLE IF NOT EXISTS score_changes (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 judge_email TEXT,
#                 poster_id TEXT,
#                 old_score INTEGER,
#                 new_score INTEGER,
#                 change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             )
#         ''')
#         db.commit()

def init_db():
    """Initialize the database with judges, judge_info, scores, and score_changes tables."""
    with app.app_context():
        db = get_db()
        # Judges table stores poster assignments
        db.execute('''
            CREATE TABLE IF NOT EXISTS judges (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                pin TEXT,
                assigned_posters TEXT,  -- Stored as JSON list of poster IDs; can be empty "[]"
                assigned_poster_titles TEXT  -- Stored as JSON mapping poster IDs to titles
            )
        ''')
        # judge_info table: judge_id is provided (from the import file)
        db.execute('''
            CREATE TABLE IF NOT EXISTS judge_info (
                judge_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
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


ranking_data = []  # Holds your poster/rank data loaded from XLSX.
# Initialize DB on first run
if not os.path.exists(DATABASE):
    init_db()
    # Insert sample judge data for demo purposes
    db = sqlite3.connect(DATABASE)
    # sample_judges = [
    #     ("judge1@example.com", "Judge One", json.dumps(["poster1", "poster2", "poster3"])),
    #     ("judge2@example.com", "Judge Two", json.dumps(["poster2", "poster4"]))
    # ]
    # db.executemany("INSERT OR IGNORE INTO judges (email, name, assigned_posters) VALUES (?, ?, ?)", sample_judges)
    # db.commit()
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
    MAIL_USERNAME='ecsresearchdayportal@gmail.com',        # Replace with your email address
    MAIL_PASSWORD='jfca enpw emcq huyv',             # Replace with your app-specific password
    MAIL_DEFAULT_SENDER='ecsresearchdayportal@gmail.com'
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Dark-themed login screen for judges.
    A judge is allowed to login only if they have at least one poster assignment.
    """
    error_message = None
    
    if request.method == 'POST':
        email = request.form.get('email')
        db = get_db()
        cur = db.execute("SELECT * FROM judges WHERE email = ?", (email,))
        judge = cur.fetchone()
        if judge:
            # Check if the judge has any assigned posters
            assigned_posters = json.loads(judge['assigned_posters']) if judge['assigned_posters'] else []
            if not assigned_posters:
                error_message = "No posters have been assigned to you. If this is a mistake, please check with the admin."
            else:
                # Otherwise, generate a 6-digit OTP and send it
                otp = str(random.randint(100000, 999999))
                otp_store[email] = otp
                send_otp(email, otp)
                session['pending_email'] = email
                flash("An OTP has been sent to your email. Please enter it below.")
                return redirect(url_for('verify'))
        else:
            error_message = "Email not authorized."
    
    # Render a dark-themed login page with a snackbar for errors
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
    /* Your existing CSS styles */
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'IBM Plex Sans', sans-serif; }
    body { background-color: #121212; color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; }
    .card { background-color: #1f1f1f; border-radius: 20px; width: 90%; max-width: 400px; padding: 2rem; }
    .title { font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem; text-align: center; }
    .input-group { margin-bottom: 1rem; }
    label { display: block; font-size: 0.9rem; margin-bottom: 0.4rem; color: #ccc; }
    input[type="email"] { width: 100%; padding: 0.8rem; border-radius: 10px; border: none; outline: none; font-size: 1rem; background-color: #2a2a2a; color: #fff; }
    .btn { display: block; width: 100%; background-color: #4285F4; color: #fff; font-size: 1rem; font-weight: 600; text-align: center; padding: 0.8rem; border: none; border-radius: 10px; margin-top: 1rem; cursor: pointer; }
    .btn:hover { background-color: #357ae8; }
    .info { font-size: 0.85rem; color: #aaa; margin-top: 0.5rem; text-align: center; }
    
    /* Snackbar styles */
    .snackbar {
      visibility: hidden;
      min-width: 300px;
      background-color: #ff9800; /* Orange for warnings */
      color: #000;
      text-align: center;
      border-radius: 10px;
      padding: 16px;
      position: fixed;
      z-index: 1;
      left: 50%;
      transform: translateX(-50%);
      bottom: 30px;
      font-size: 0.95rem;
      font-weight: 600;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    }
    
    .snackbar.show {
      visibility: visible;
      animation: fadein 0.5s, fadeout 0.5s 19.5s;
    }
    
    @keyframes fadein {
      from {bottom: 0; opacity: 0;}
      to {bottom: 30px; opacity: 1;}
    }
    
    @keyframes fadeout {
      from {bottom: 30px; opacity: 1;}
      to {bottom: 0; opacity: 0;}
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="title">ECS Research Day Portal</div>
    <form method="post">
      <div class="input-group">
        <label for="email">Enter your email</label>
        <input type="email" id="email" name="email" placeholder="your.email@syr.edu" required />
      </div>
      <button type="submit" class="btn">Send OTP</button>
      <div class="info">Build for Syracuse University 🍊</div>
    </form>
  </div>
  
  <!-- Snackbar for error messages -->
  <div id="snackbar" class="snackbar">{{ error_message }}</div>
  
  <script>
    // Show snackbar if there's an error message
    {% if error_message %}
      (function(){
        var snackbar = document.getElementById("snackbar");
        snackbar.className = "snackbar show";
        
        // Hide snackbar after 4 seconds
        setTimeout(function() {
          snackbar.className = snackbar.className.replace("show", "");
        }, 3000);
      })();
    {% endif %}
  </script>
</body>
</html>
    ''', error_message=error_message)


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    pending_email = session.get('pending_email')
    if not pending_email:
        return redirect(url_for('login'))

    if request.method == 'POST':
        otp_input = (
            request.form.get('otp1', '') +
            request.form.get('otp2', '') +
            request.form.get('otp3', '') +
            request.form.get('otp4', '') +
            request.form.get('otp5', '') +
            request.form.get('otp6', '')
        )
        
        if otp_store.get(pending_email) == otp_input:
            session['user'] = pending_email
            otp_store.pop(pending_email, None)
            flash("Logged in successfully.")
            # Check if there is a redirect URL saved from a QR scan
            redirect_url = session.pop('redirect_after_login', None)
            if redirect_url:
                return redirect(redirect_url)
            else:
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


@app.route('/dashboard')
def dashboard():
    """
    Dark-theme dashboard that greets the judge and shows the assigned posters.
    Displays each poster in the format "poster_number: Poster_name".
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
    
    # Load the assigned posters (list of poster ids) and the poster title mapping.
    assigned_posters = json.loads(judge['assigned_posters']) if judge['assigned_posters'] else []
    poster_titles = json.loads(judge['assigned_poster_titles']) if judge['assigned_poster_titles'] else {}

    # Retrieve existing scores for these posters.
    scores = {}
    for poster in assigned_posters:
        cur = db.execute(
            "SELECT score FROM scores WHERE judge_email = ? AND poster_id = ?",
            (email, poster)
        )
        row = cur.fetchone()
        scores[poster] = row['score'] if row else None

    # Render the dashboard template.
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
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'IBM Plex Sans', sans-serif; }
    body { background-color: #121212; color: #fff; }
    .header { background-color: #1f1f1f; border-bottom-left-radius: 24px; border-bottom-right-radius: 24px; padding: 2rem 1.5rem; }
    .header .top-row { display: flex; align-items: center; justify-content: space-between; }
    .header .greeting h2 { font-size: 1.2rem; font-weight: 600; margin-bottom: 0.2rem; }
    .header .greeting span { font-size: 0.9rem; color: #ccc; }
    .main-content { margin-top: 1rem; padding: 1.5rem; }
    .poster-list { display: flex; flex-direction: column; gap: 1rem; }
    .poster-card { background-color: #1f1f1f; border-radius: 12px; padding: 1rem; display: flex; align-items: center; justify-content: space-between; }
    .poster-info { display: flex; flex-direction: column; }
    .poster-name { font-weight: 600; margin-bottom: 0.3rem; }
    .poster-score { color: #999; font-size: 0.9rem; }
    .score-link { color: #fff; background-color: #4285F4; padding: 0.4rem 0.6rem; border-radius: 8px; text-decoration: none; font-size: 0.85rem; }
    .score-link:hover { background-color: #357ae8; }
    .bottom-links { display: flex; justify-content: space-around; margin-top: 2rem; }
    .bottom-links a { text-decoration: none; color: #fff; background: #4285F4; padding: 0.6rem 1.2rem; border-radius: 8px; transition: background 0.2s ease-in-out; }
    .bottom-links a:hover { background: #357ae8; }
    .top-row a {
      text-decoration: none;
      color: #fff;
      background: red;
      padding: 0.6rem 1.2rem;
      border-radius: 8px;
      transition: background 0.2s ease-in-out;
    }
  </style>
</head>
<body>
  <!-- Header -->
  <div class="header">
    <div class="top-row">
      <div class="greeting">
        <h2>Hi &#128075; {{ judge.name }}!</h2>
        <span>Welcome back</span>
      </div>
      <div class="top-row">
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
          <!-- Extract poster number from the poster id and show in the format: poster_number: Poster_name -->
          <span class="poster-name">
            Poster-{{ poster[6:] }}: {{ poster_titles.get(poster, 'No Title') }}
          </span>
          {% if scores[poster] is not none %}
            <span class="poster-score">Score: {{ scores[poster] }}</span>
          {% else %}
            <span class="poster-score">Not Scored</span>
          {% endif %}
        </div>
        <a class="score-link" href="{{ url_for('score', poster_id=poster) }}">Update</a>
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
    judge=judge,
    assigned_posters=assigned_posters,
    poster_titles=poster_titles,
    scores=scores
    )
    
    return dashboard_html


@app.route('/score/<poster_id>', methods=['GET', 'POST'])
def score(poster_id):
    """
    Allows a judge to enter or update a score for an assigned poster.
    Displays the poster in the format "poster_number: Poster_name" at the top.
    Uses a mobile-optimized UI and follows the dark theme.
    """
    if 'user' not in session:
        return redirect(url_for('login'))
    email = session['user']
    db = get_db()
    # Fetch both assigned_posters and assigned_poster_titles
    cur = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges WHERE email = ?", (email,))
    row = cur.fetchone()
    if not row:
        flash("Judge not found.")
        return redirect(url_for('login'))
    assigned_posters = json.loads(row['assigned_posters']) if row['assigned_posters'] else []
    poster_titles = json.loads(row['assigned_poster_titles']) if row['assigned_poster_titles'] else {}
    if poster_id not in assigned_posters:
        flash("You are not assigned to this poster.")
        return redirect(url_for('dashboard'))
    
    # Compute display string in the format "poster_number: Poster_name"
    poster_display = f"{poster_id[6:]}: {poster_titles.get(poster_id, 'No Title')}"
    
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
        
        # Check if there is an existing score
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
  <title>Enter Score for {{ poster_display }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: #121212; font-family: 'Roboto', sans-serif; color: white; }
    .card { border-radius: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); background: #1f1f1f; }
    .score-input { font-size: 2rem; text-align: center; border: none; outline: none; width: 100%; background-color: transparent; color: white; }
    .submit-btn { background-color: #4285F4; border: none; color: white; font-size: 1.5rem; border-radius: 10px; padding: 10px 0; margin-top: 20px; width: 100%; }
    .submit-btn:hover { background-color: #357ae8; }
    .text-color-w { color: white; }
    .back-btn { padding: .5em; background-color: #4285F4; text-decoration: none; color: white; border-radius: 10px; }
  </style>
</head>
<body>
  <div class="container d-flex justify-content-center align-items-center vh-100">
    <div class="card p-4" style="width: 90%; max-width: 400px;">
      <h2 class="text-color-w text-center mb-4">Enter Score</h2>
      <!-- Display the poster number and title in the desired format -->
      <h5 class="text-center mb-4 text-color-w">{{ poster_display }}</h5>
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
''', poster_display=poster_display, current_score=current_score)



# ===============================
# Score Change Log for Judges
# ===============================
@app.route('/score_log')
def score_log():
    """
    Display the log of score changes as a dark-themed timeline,
    matching the style of the main dashboard screen.
    Indicates when scores were modified by an admin.
    """
    if 'user' not in session:
        return redirect(url_for('login'))
    
    email = session['user']
    base_email = email.split(" [ADMIN]")[0]  # Handle case where email might have [ADMIN] suffix
    
    db = get_db()
    # Fetch changes in descending chronological order
    # Use LIKE query to match both normal emails and emails with [ADMIN] suffix
    cur = db.execute("""
        SELECT * FROM score_changes 
        WHERE judge_email LIKE ? OR judge_email LIKE ? 
        ORDER BY change_time DESC
    """, (base_email, base_email + " [ADMIN]%"))
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
    .admin-dot {
      background-color: #ff9800; /* different color for admin changes */
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
    .admin-badge {
      display: inline-block;
      background-color: #ff9800;
      color: #000;
      font-size: 0.7rem;
      font-weight: bold;
      padding: 0.1rem 0.3rem;
      border-radius: 4px;
      margin-left: 0.5rem;
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
          <div class="timeline-dot {% if '[ADMIN]' in change['judge_email'] %}admin-dot{% endif %}"></div>
          <div class="item-content">
            <div class="time-stamp">{{ change['change_time'] }}</div>
            <div class="poster-id">
              Poster: {{ change['poster_id'] }}
              {% if '[ADMIN]' in change['judge_email'] %}
                <span class="admin-badge">ADMIN</span>
              {% endif %}
            </div>
            <div class="score-change">
              <!-- If old_score is None, it means first-time score creation -->
              {% if change['old_score'] is none %}
                {% if '[ADMIN]' in change['judge_email'] %}
                  Score assigned by admin: <span>{{ change['new_score'] }}</span>
                {% else %}
                  Initial score set to <span>{{ change['new_score'] }}</span>
                {% endif %}
              {% else %}
                {% if '[ADMIN]' in change['judge_email'] %}
                  Score changed by admin from <span>{{ change['old_score'] }}</span> to <span>{{ change['new_score'] }}</span>
                {% else %}
                  Changed from <span>{{ change['old_score'] }}</span> to <span>{{ change['new_score'] }}</span>
                {% endif %}
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

@app.route('/admin/remove_judges', methods=['GET', 'POST'])
def remove_judges():
    """
    Admin-only endpoint (accessible only if ?key=adminsecret is provided)
    to remove all current judges from the database.
    
    GET: Displays a dark-themed confirmation form.
    POST: Deletes all rows from the judges table.
    """
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401

    if request.method == 'POST':
        db = get_db()
        db.execute("DELETE FROM judges")
        db.commit()
        reset_scores()
        return "All judges have been removed.", 200

    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Remove Judges</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet"
                  href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
            <style>
                body {
                  background-color: #121212;
                  color: #fff;
                  font-family: 'IBM Plex Sans', sans-serif;
                  margin: 0;
                  padding: 2rem;
                }
                .container {
                  max-width: 500px;
                  margin: auto;
                  background: #1f1f1f;
                  padding: 2rem;
                  border-radius: 12px;
                  box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                  text-align: center;
                }
                h2 { margin-bottom: 1rem; }
                p { margin-bottom: 2rem; }
                button {
                  padding: 0.5rem 1rem;
                  background: #d9534f;
                  color: #fff;
                  border: none;
                  border-radius: 8px;
                  cursor: pointer;
                  font-size: 1rem;
                }
                button:hover {
                  background: #c9302c;
                }
                a.btn {
                  display: inline-block;
                  margin-top: 1rem;
                  padding: 0.5rem 1rem;
                  background: #4285F4;
                  color: #fff;
                  border-radius: 8px;
                  text-decoration: none;
                  font-size: 1rem;
                }
                a.btn:hover {
                  background: #357ae8;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Remove All Judges</h2>
                <p>Are you sure you want to remove all judges from the system?<br>
                   This action cannot be undone.</p>
                <form method="POST">
                    <button type="submit">Remove Judges</button>
                </form>
                <a href="{{ url_for('admin_dashboard') }}?key=adminsecret" class="btn">Cancel</a>
            </div>
        </body>
        </html>
    ''')


import openpyxl  # pip install openpyxl

def is_valid_poster(cell_value):
    """Return True if the cell value represents a valid poster number."""
    try:
        return cell_value is not None and (isinstance(cell_value, (int, float)) or str(cell_value).strip() != "")
    except Exception:
        return False

@app.route('/admin/import_judges', methods=['GET', 'POST'])
def import_judges():
    """
    Admin-only endpoint (accessible only if ?key=adminsecret is provided)
    that accepts an XLSX file upload containing judge and poster assignments.
    
    Expected header columns include:
      - Judge, Judge FirstName, Judge LastName, Email,
        poster-1, poster-1-title, poster-2, poster-2-title, ... poster-6, poster-6-title
      
    All judges are saved in the judges table.  
    Judges with no poster assignment will have an empty list in assigned_posters.
    """
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401

    if request.method == 'GET':
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Import Judges</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet"
                  href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
            <style>
                body {
                  background-color: #121212;
                  color: #fff;
                  font-family: 'IBM Plex Sans', sans-serif;
                  margin: 0;
                  padding: 2rem;
                }
                .container {
                  max-width: 500px;
                  margin: auto;
                  background: #1f1f1f;
                  padding: 2rem;
                  border-radius: 12px;
                  box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                  text-align: center;
                }
                input[type="file"] {
                  display: block;
                  margin: 1rem auto;
                  background: #2a2a2a;
                  color: #fff;
                  border: none;
                  padding: 0.5rem;
                  border-radius: 8px;
                }
                button {
                  padding: 0.5rem 1rem;
                  background: #4285F4;
                  color: #fff;
                  border: none;
                  border-radius: 8px;
                  cursor: pointer;
                  font-size: 1rem;
                }
                button:hover {
                  background: #357ae8;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Import Judges from XLSX</h2>
                <form method="POST" enctype="multipart/form-data">
                    <input type="file" name="file" accept=".xlsx" required>
                    <button type="submit">Upload</button>
                </form>
            </div>
        </body>
        </html>
        ''')
    
    # POST: Process the file
    uploaded_file = request.files.get('file')
    if not uploaded_file:
        return "No file uploaded", 400

    try:
        wb = openpyxl.load_workbook(uploaded_file)
        sheet = wb.active

        # Read header row
        headers = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
        
        # Required columns: Judge, Judge FirstName, Judge LastName, Email
        try:
            judge_id_index = headers.index("Judge")
            fname_index = headers.index("Judge FirstName")
            lname_index = headers.index("Judge LastName")
            email_index = headers.index("Email")
        except ValueError as e:
            return f"Missing required column in header: {str(e)}", 400

        # Determine indexes for poster and poster-title columns (poster-1 .. poster-6)
        poster_cols = {}
        poster_title_cols = {}
        for i in range(1, 7):
            try:
                poster_cols[i] = headers.index(f"poster-{i}")
            except ValueError:
                poster_cols[i] = None
            try:
                poster_title_cols[i] = headers.index(f"poster-{i}-title")
            except ValueError:
                poster_title_cols[i] = None

        imported_count = 0
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        for row in sheet.iter_rows(min_row=2):
            judge_id = row[judge_id_index].value
            if judge_id is None:
                continue
            first_name = row[fname_index].value or ""
            last_name = row[lname_index].value or ""
            full_name = f"{first_name.strip()} {last_name.strip()}".strip()
            email = row[email_index].value
            if not email:
                continue

            assigned_posters = []
            poster_titles = {}
            for i in range(1, 7):
                p_col = poster_cols.get(i)
                if p_col is not None:
                    cell_value = row[p_col].value
                    if is_valid_poster(cell_value):
                        try:
                            poster_num = int(float(cell_value))
                        except Exception:
                            continue
                        poster_id = f"poster{poster_num}"
                        if poster_id not in assigned_posters:
                            assigned_posters.append(poster_id)
                            t_col = poster_title_cols.get(i)
                            title = row[t_col].value if t_col is not None else None
                            if title:
                                poster_titles[poster_id] = title.strip()

            # Save judge in the judges table even if no posters are assigned.
            db.execute("""
                INSERT INTO judges (email, name, assigned_posters, assigned_poster_titles)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    name = excluded.name,
                    assigned_posters = excluded.assigned_posters,
                    assigned_poster_titles = excluded.assigned_poster_titles
            """, (email.strip(), full_name, json.dumps(assigned_posters), json.dumps(poster_titles)))
            # Save judge info with provided judge_id
            db.execute("""
                INSERT OR REPLACE INTO judge_info (judge_id, name, email)
                VALUES (?, ?, ?)
            """, (judge_id, full_name, email.strip()))
            imported_count += 1

        db.commit()
        db.close()

        return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
           <meta charset="UTF-8">
           <meta name="viewport" content="width=device-width, initial-scale=1.0">
           <title>Import Successful</title>
           <link rel="stylesheet"
                 href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
           <style>
              body {
                 background-color: #121212;
                 color: #fff;
                 font-family: 'IBM Plex Sans', sans-serif;
                 padding: 2rem;
                 text-align: center;
              }
              .container {
                 max-width: 500px;
                 margin: auto;
                 background: #1f1f1f;
                 padding: 2rem;
                 border-radius: 12px;
                 box-shadow: 0 4px 6px rgba(0,0,0,0.3);
              }
              a.btn {
                 display: inline-block;
                 margin-top: 1rem;
                 padding: 0.5rem 1rem;
                 background: #4285F4;
                 color: #fff;
                 border-radius: 8px;
                 text-decoration: none;
                 font-size: 1rem;
              }
              a.btn:hover {
                 background: #357ae8;
              }
           </style>
        </head>
        <body>
           <div class="container">
              <h2>Import Successful</h2>
              <p>{{ imported_count }} judges imported successfully.</p>
              <a href="{{ url_for('admin_dashboard') }}?key=adminsecret" class="btn">Back to Admin Dashboard</a>
           </div>
        </body>
        </html>
        ''', imported_count=imported_count), 200

    except Exception as e:
        return f"Error processing file: {str(e)}", 500

@app.route('/admin/export_score_matrix')
def export_score_matrix():
    """
    Admin-only endpoint to export a score matrix in XLSX format.
    The matrix rows represent posters (e.g. "Poster-1", "Poster-2", …)
    and the columns represent judges (e.g. "Judge-1", "Judge-2", …).
    Each cell shows the score given by that judge to that poster (or 0 if not scored).
    Access is protected by a simple query parameter key (e.g., ?key=adminsecret).
    """
    # Check admin access via the key
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401

    db = get_db()

    # 1. Get the list of judges (using the judge_info table) sorted by judge_id.
    judges = db.execute("SELECT judge_id, email FROM judge_info ORDER BY judge_id").fetchall()
    judge_list = [{'id': judge['judge_id'], 'email': judge['email']} for judge in judges]

    # 2. Build a set of all poster IDs.
    #    We include poster ids from the scores table and from the judges' assigned_posters.
    poster_set = set()

    # From the scores table:
    score_rows = db.execute("SELECT DISTINCT poster_id FROM scores").fetchall()
    for row in score_rows:
        if row['poster_id']:
            poster_set.add(row['poster_id'])

    # From each judge's assigned_posters (stored as JSON):
    judges_all = db.execute("SELECT assigned_posters FROM judges").fetchall()
    for row in judges_all:
        assigned = row['assigned_posters']
        if assigned:
            try:
                posters = json.loads(assigned)
                for p in posters:
                    poster_set.add(p)
            except Exception:
                pass

    # Sort the poster list by the numeric portion.
    def poster_sort_key(p):
        try:
            return int(p.replace("poster", ""))
        except Exception:
            return 0
    poster_list = sorted(list(poster_set), key=poster_sort_key)

    # 3. Build a dictionary of scores keyed by (poster_id, judge_email).
    #    If a judge has not scored a poster, the default will be 0.
    score_rows = db.execute("SELECT judge_email, poster_id, score FROM scores").fetchall()
    score_dict = {}
    for row in score_rows:
        score_dict[(row['poster_id'], row['judge_email'])] = row['score']

    # 4. Create a new XLSX workbook and worksheet using openpyxl.
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Score Matrix"

    # Write header row.
    # The first cell in the header row is left blank; then one column per judge.
    ws.cell(row=1, column=1, value="")  # Top-left cell is blank.
    col_index = 2
    for judge in judge_list:
        header = f"Judge-{judge['id']}"
        ws.cell(row=1, column=col_index, value=header)
        col_index += 1

    # 5. Write each poster row.
    # The first column contains the poster label (e.g., "Poster-1"),
    # and the subsequent columns contain the score for each judge (or 0 if no score exists).
    row_index = 2
    for poster in poster_list:
        try:
            poster_num = int(poster.replace("poster", ""))
        except Exception:
            poster_num = poster
        ws.cell(row=row_index, column=1, value=f"Poster-{poster_num}")
        col_index = 2
        for judge in judge_list:
            # Get the score if it exists; otherwise use 0.
            score_value = score_dict.get((poster, judge['email']), 0)
            ws.cell(row=row_index, column=col_index, value=score_value)
            col_index += 1
        row_index += 1

    # 6. Save the workbook to a BytesIO stream.
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # 7. Return the XLSX file as an attachment.
    return send_file(output,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True,
                     download_name="score_matrix.xlsx")


@app.route('/qr/<poster_id>')
def qr_redirect(poster_id):
    """
    QR endpoint: When a judge scans a QR code pointing to /qr/<poster_id>,
    if logged in, they are immediately redirected to /score/<poster_id>.
    Otherwise, the intended URL is saved in the session and the judge is sent to login.
    """
    if 'user' in session:
        return redirect(url_for('score', poster_id=poster_id))
    else:
        # Save the intended redirect URL for after login
        session['redirect_after_login'] = url_for('score', poster_id=poster_id)
        return redirect(url_for('login'))



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


@app.route('/admin/view_scores', methods=['GET'])
def admin_view_scores():
    # Check admin access using query parameter
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401

    db = get_db()
    
    # Get all judges who have poster assignments
    judges = db.execute("SELECT email, name, assigned_posters, assigned_poster_titles FROM judges").fetchall()
    
    # Build a list of all judge-poster assignments with scores (if they exist)
    all_assignments = []
    
    for judge in judges:
        email = judge['email']
        name = judge['name']
        
        if not judge['assigned_posters']:
            continue  # Skip judges with no assigned posters
        
        assigned_posters = json.loads(judge['assigned_posters'])
        poster_titles = json.loads(judge['assigned_poster_titles']) if judge['assigned_poster_titles'] else {}
        
        for poster_id in assigned_posters:
            # Check if a score exists for this judge-poster pair
            cur = db.execute(
                "SELECT id, score FROM scores WHERE judge_email = ? AND poster_id = ?", 
                (email, poster_id)
            )
            score_row = cur.fetchone()
            
            # Add to our combined view, whether scored or not
            all_assignments.append({
                'judge_email': email,
                'judge_name': name,
                'poster_id': poster_id,
                'poster_title': poster_titles.get(poster_id, "No Title"),
                'score_id': score_row['id'] if score_row else None,
                'score': score_row['score'] if score_row else None,
            })
    
    # Sort by judge email, then by poster ID for a consistent view
    all_assignments.sort(key=lambda x: (x['judge_email'], x['poster_id']))
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>View/Edit Scores</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
      <style>
        body {
          background-color: #121212;
          color: #fff;
          font-family: 'IBM Plex Sans', sans-serif;
          padding: 1rem;
        }
        h1 {
          font-size: 1.8rem;
          margin-bottom: 1.5rem;
          text-align: center;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 2rem;
        }
        th, td {
          border: 1px solid #2a2a2a;
          padding: 0.5rem;
          text-align: left;
        }
        th {
          background-color: #1f1f1f;
        }
        tr:nth-child(even) {
          background-color: #1f1f1f;
        }
        .btn {
          background-color: #4285F4;
          color: #fff;
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 8px;
          text-decoration: none;
          cursor: pointer;
          display: inline-block;
          font-size: 0.9rem;
          text-align: center;
        }
        .btn:hover {
          background-color: #357ae8;
        }
        .form-inline {
          display: flex;
          gap: 0.5rem;
          align-items: center;
          justify-content: center;
        }
        input[type="number"] {
          width: 80px;
          padding: 0.5rem 0;
          border-radius: 4px;
          border: none;
          text-align: center;
          font-size: 1rem;
        }
        .not-scored {
          color: #ff9800;
          font-style: italic;
        }
        .back-link {
          display: block;
          text-align: center;
          margin-bottom: 2rem;
        }
        
        /* Card view for mobile devices */
        .score-card {
          display: none;
          background-color: #1f1f1f;
          border-radius: 10px;
          padding: 1rem;
          margin-bottom: 1rem;
        }
        .card-field {
          margin-bottom: 0.5rem;
        }
        .card-label {
          font-size: 0.8rem;
          color: #aaa;
          display: block;
          margin-bottom: 0.2rem;
        }
        .card-value {
          font-size: 1rem;
        }
        .card-action {
          margin-top: 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        .card-action .form-inline {
          flex-direction: column;
        }
        .card-action input[type="number"] {
          width: 100%;
        }
        
        /* Responsive styles */
        @media (max-width: 768px) {
          h1 {
            font-size: 1.5rem;
          }
          .desktop-table {
            display: none;  /* Hide the table on mobile */
          }
          .score-card {
            display: block;  /* Show cards on mobile */
          }
          .btn {
            width: 100%;
            padding: 0.8rem;
          }
        }
      </style>
    </head>
    <body>
      <h1>View/Edit Scores</h1>
      
      <!-- Desktop table view (hidden on mobile) -->
      <table class="desktop-table">
        <thead>
          <tr>
            <th>Judge Email</th>
            <th>Judge Name</th>
            <th>Poster ID</th>
            <th>Poster Title</th>
            <th>Score</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {% for assignment in all_assignments %}
          <tr>
            <td>{{ assignment.judge_email }}</td>
            <td>{{ assignment.judge_name }}</td>
            <td>{{ assignment.poster_id }}</td>
            <td>{{ assignment.poster_title }}</td>
            <td>
              {% if assignment.score is not none %}
                {{ assignment.score }}
              {% else %}
                <span class="not-scored">Not scored yet</span>
              {% endif %}
            </td>
            <td>
              {% if assignment.score_id is not none %}
                <!-- For existing scores, allow editing -->
                <form class="form-inline" method="POST" action="{{ url_for('admin_edit_score') }}?key=adminsecret">
                  <input type="hidden" name="score_id" value="{{ assignment.score_id }}">
                  <input type="number" name="new_score" min="0" max="10" placeholder="0-10" required>
                  <button type="submit" class="btn">Update</button>
                </form>
              {% else %}
                <!-- For unscored assignments, allow adding a score -->
                <form class="form-inline" method="POST" action="{{ url_for('admin_add_score') }}?key=adminsecret">
                  <input type="hidden" name="judge_email" value="{{ assignment.judge_email }}">
                  <input type="hidden" name="poster_id" value="{{ assignment.poster_id }}">
                  <input type="number" name="score" min="0" max="10" placeholder="0-10" required>
                  <button type="submit" class="btn">Add</button>
                </form>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      
      <!-- Mobile card view (hidden on desktop) -->
      {% for assignment in all_assignments %}
      <div class="score-card">
        <div class="card-field">
          <span class="card-label">Judge Email:</span>
          <span class="card-value">{{ assignment.judge_email }}</span>
        </div>
        <div class="card-field">
          <span class="card-label">Judge Name:</span>
          <span class="card-value">{{ assignment.judge_name }}</span>
        </div>
        <div class="card-field">
          <span class="card-label">Poster ID:</span>
          <span class="card-value">{{ assignment.poster_id }}</span>
        </div>
        <div class="card-field">
          <span class="card-label">Poster Title:</span>
          <span class="card-value">{{ assignment.poster_title }}</span>
        </div>
        <div class="card-field">
          <span class="card-label">Score:</span>
          <span class="card-value">
            {% if assignment.score is not none %}
              {{ assignment.score }}
            {% else %}
              <span class="not-scored">Not scored yet</span>
            {% endif %}
          </span>
        </div>
        <div class="card-action">
          {% if assignment.score_id is not none %}
            <!-- For existing scores, allow editing -->
            <form class="form-inline" method="POST" action="{{ url_for('admin_edit_score') }}?key=adminsecret">
              <input type="hidden" name="score_id" value="{{ assignment.score_id }}">
              <input type="number" name="new_score" min="0" max="10" placeholder="0-10" required>
              <button type="submit" class="btn">Update Score</button>
            </form>
          {% else %}
            <!-- For unscored assignments, allow adding a score -->
            <form class="form-inline" method="POST" action="{{ url_for('admin_add_score') }}?key=adminsecret">
              <input type="hidden" name="judge_email" value="{{ assignment.judge_email }}">
              <input type="hidden" name="poster_id" value="{{ assignment.poster_id }}">
              <input type="number" name="score" min="0" max="10" placeholder="0-10" required>
              <button type="submit" class="btn">Add Score</button>
            </form>
          {% endif %}
        </div>
      </div>
      {% endfor %}
      
      <div class="back-link">
        <a href="{{ url_for('admin_dashboard') }}?key=adminsecret" class="btn">Back to Admin Dashboard</a>
      </div>
    </body>
    </html>
    ''', all_assignments=all_assignments)
    
@app.route('/admin/add_score', methods=['POST'])
def admin_add_score():
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401

    judge_email = request.form.get('judge_email')
    poster_id = request.form.get('poster_id')
    score = request.form.get('score')
    
    try:
        score_int = int(score)
        if score_int < 0 or score_int > 10:
            flash("Score must be between 0 and 10.")
            return redirect(url_for('admin_view_scores') + "?key=adminsecret")
    except ValueError:
        flash("Invalid score input.")
        return redirect(url_for('admin_view_scores') + "?key=adminsecret")

    db = get_db()
    # Insert the new score
    db.execute(
        "INSERT INTO scores (judge_email, poster_id, score) VALUES (?, ?, ?)",
        (judge_email, poster_id, score_int)
    )
    # Also log this in score_changes - add '[ADMIN]' to indicate admin action
    db.execute(
        "INSERT INTO score_changes (judge_email, poster_id, old_score, new_score) VALUES (?, ?, ?, ?)",
        (judge_email + " [ADMIN]", poster_id, None, score_int)
    )
    db.commit()
    
    flash("Score added.")
    return redirect(url_for('admin_view_scores') + "?key=adminsecret")

# @app.route('/admin/edit_score', methods=['POST'])
# def admin_edit_score():
@app.route('/admin/edit_score', methods=['POST'])
def admin_edit_score():
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401

    score_id = request.form.get('score_id')
    new_score = request.form.get('new_score')
    try:
        new_score = int(new_score)
        if new_score < 0 or new_score > 10:
            flash("Score must be between 0 and 10.")
            return redirect(url_for('admin_view_scores') + "?key=adminsecret")
    except ValueError:
        flash("Invalid score input.")
        return redirect(url_for('admin_view_scores') + "?key=adminsecret")

    db = get_db()
    
    # Get the current score details before updating
    cur = db.execute("SELECT judge_email, poster_id, score FROM scores WHERE id = ?", (score_id,))
    score_row = cur.fetchone()
    if not score_row:
        flash("Score not found.")
        return redirect(url_for('admin_view_scores') + "?key=adminsecret")
    
    judge_email = score_row['judge_email']
    poster_id = score_row['poster_id']
    old_score = score_row['score']
    
    # Update the score in the scores table
    db.execute("UPDATE scores SET score = ? WHERE id = ?", (new_score, score_id))
    
    # Log the change in score_changes - add '[ADMIN]' to indicate admin action
    db.execute(
        "INSERT INTO score_changes (judge_email, poster_id, old_score, new_score) VALUES (?, ?, ?, ?)",
        (judge_email + " [ADMIN]", poster_id, old_score, new_score)
    )
    
    db.commit()
    flash("Score updated.")
    return redirect(url_for('admin_view_scores') + "?key=adminsecret")
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401

    score_id = request.form.get('score_id')
    new_score = request.form.get('new_score')
    try:
        new_score = int(new_score)
        if new_score < 0 or new_score > 10:
            flash("Score must be between 0 and 10.")
            return redirect(url_for('admin_view_scores') + "?key=adminsecret")
    except ValueError:
        flash("Invalid score input.")
        return redirect(url_for('admin_view_scores') + "?key=adminsecret")

    db = get_db()
    # Update the score in the scores table
    db.execute("UPDATE scores SET score = ? WHERE id = ?", (new_score, score_id))
    db.commit()
    flash("Score updated.")
    return redirect(url_for('admin_view_scores') + "?key=adminsecret")

@app.route('/admin/reset_scores', methods=['GET', 'POST'])
def reset_scores():
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401

    if request.method == 'GET':
        return render_template_string('''
         <!DOCTYPE html>
         <html lang="en">
         <head>
             <meta charset="UTF-8">
             <title>Reset Scores</title>
             <meta name="viewport" content="width=device-width, initial-scale=1.0">
             <link rel="stylesheet"
                   href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
             <style>
                 body { background-color: #121212; color: #fff; font-family: 'IBM Plex Sans', sans-serif; padding: 2rem; }
                 .container { max-width: 500px; margin: auto; background: #1f1f1f; padding: 1rem; border-radius: 8px; text-align: center; }
                 .btn { background-color: #4285F4; color: #fff; padding: 0.5rem 1rem; border: none; border-radius: 8px; text-decoration: none; cursor: pointer; }
                 .btn:hover { background-color: #357ae8; }
             </style>
         </head>
         <body>
             <div class="container">
                 <h2>Reset Score Data</h2>
                 <p>Are you sure you want to reset all score data?<br>
                    This will remove all entries from the scores and score_changes tables.</p>
                 <form method="POST">
                     <button type="submit" class="btn">Reset Scores</button>
                 </form>
                 <br>
                 <a href="{{ url_for('admin_dashboard') }}?key=adminsecret" class="btn">Cancel</a>
             </div>
         </body>
         </html>
        ''')
    # POST: Reset the scores and score_changes tables
    db = get_db()
    db.execute("DELETE FROM scores")
    db.execute("DELETE FROM score_changes")
    db.commit()
    flash("All score data has been reset.")
    return redirect(url_for('admin_dashboard') + "?key=adminsecret")


@app.route('/admin/generate_all_qr', methods=['GET'])
def admin_generate_all_qr():
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401

    db = get_db()
    cur = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges")
    unique_posters = {}
    for row in cur.fetchall():
        # Decode the assigned posters (JSON list) and poster titles (JSON dict)
        if row['assigned_posters']:
            try:
                posters = json.loads(row['assigned_posters'])
            except Exception:
                posters = []
        else:
            posters = []
        if row['assigned_poster_titles']:
            try:
                titles = json.loads(row['assigned_poster_titles'])
            except Exception:
                titles = {}
        else:
            titles = {}
        for poster in posters:
            # Add the poster if not already included.
            if poster not in unique_posters:
                unique_posters[poster] = titles.get(poster, "No Title")

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>QR Codes for All Posters</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet" 
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
      <style>
         body {
            background-color: #121212;
            color: #fff;
            font-family: 'IBM Plex Sans', sans-serif;
            padding: 2rem;
         }
         .container {
            max-width: 900px;
            margin: auto;
            background: #1f1f1f;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
         }
         .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
         }
         .poster-card {
            border: 1px solid #2a2a2a;
            padding: 1rem;
            text-align: center;
            border-radius: 8px;
            background-color: #121212;
         }
         .poster-card h3 {
            margin-bottom: 0.5rem;
         }
         .poster-card img {
            margin-top: 0.5rem;
            width: 150px;
            height: 150px;
         }
         .btn {
            display: inline-block;
            margin-top: 1rem;
            padding: 0.5rem 1rem;
            background: #4285F4;
            color: #fff;
            border-radius: 8px;
            text-decoration: none;
            font-size: 1rem;
            cursor: pointer;
         }
         .btn:hover {
            background: #357ae8;
         }
         .print-btn {
            background: #5cb85c;
         }
         .print-btn:hover {
            background: #4cae4c;
         }
      </style>
      <script>
         function printPage() {
           window.print();
         }
      </script>
    </head>
    <body>
      <div class="container">
         <h2>QR Codes for All Posters</h2>
         <div class="grid">
         {% for poster_id, title in unique_posters.items() %}
            <div class="poster-card">
               <h3>{{ poster_id[6:] }}: {{ title }}</h3>
               <img src="{{ url_for('generate_qr', poster_id=poster_id, _external=True) }}" alt="QR for {{ poster_id }}">
            </div>
         {% endfor %}
         </div>
         <button class="btn print-btn" onclick="printPage()">Print QR Codes</button>
         <br>
         <a href="{{ url_for('admin_dashboard') }}?key=adminsecret" class="btn">Back to Admin Dashboard</a>
      </div>
    </body>
    </html>
    ''', unique_posters=unique_posters)


@app.route('/admin/dashboard')
def admin_dashboard():
    # Check admin key
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401

    # Render the dashboard with a new "View Final Results" tile
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Admin Dashboard</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
      <style>
        body {
          background-color: #121212;
          color: #fff;
          font-family: 'IBM Plex Sans', sans-serif;
          margin: 0;
          padding: 0;
        }
        .header {
          background-color: #1f1f1f;
          padding: 2rem 1.5rem;
          text-align: center;
          border-bottom-left-radius: 24px;
          border-bottom-right-radius: 24px;
        }
        .header h1 {
          font-size: 2rem;
          margin-bottom: 0.5rem;
        }
        .container {
          padding: 2rem;
          max-width: 800px;
          margin: 2rem auto;
        }
        .dashboard-menu {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
          justify-content: center;
        }
        .menu-item {
          background-color: #1f1f1f;
          border-radius: 12px;
          padding: 1rem;
          width: 250px;
          text-align: center;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          transition: background-color 0.2s ease;
        }
        .menu-item:hover {
          background-color: #2a2a2a;
        }
        .menu-item h2 {
          font-size: 1.5rem;
          margin-bottom: 0.5rem;
        }
        .menu-item p {
          font-size: 1rem;
          margin-bottom: 1rem;
        }
        .menu-item a {
          display: inline-block;
          margin-top: 0.5rem;
          color: #4285F4;
          text-decoration: none;
          font-weight: 600;
          padding: 0.5rem 1rem;
          border: 2px solid #4285F4;
          border-radius: 8px;
          transition: background-color 0.2s ease;
        }
        .menu-item a:hover {
          background-color: #4285F4;
          color: #fff;
        }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>Admin Dashboard</h1>
        <p>Manage all admin operations from here</p>
      </div>
      <div class="container">
        <div class="dashboard-menu">
          <!-- Existing Admin Tiles -->
          <div class="menu-item">
            <h2>Import Judges</h2>
            <p>Upload an XLSX file to import judges and poster assignments.</p>
            <a href="{{ url_for('import_judges') }}?key=adminsecret">Go to Import</a>
          </div>
          <div class="menu-item">
            <h2>Remove Judges</h2>
            <p>Remove all current judges from the system.</p>
            <a href="{{ url_for('remove_judges') }}?key=adminsecret">Remove Judges</a>
          </div>
          <div class="menu-item">
            <h2>Export Scores</h2>
            <p>Download all scores as a CSV file.</p>
            <a href="{{ url_for('export') }}?key=adminsecret">Export CSV</a>
          </div>
          <div class="menu-item">
            <h2>View/Edit Scores</h2>
            <p>Review and update scores submitted by judges.</p>
            <a href="{{ url_for('admin_view_scores') }}?key=adminsecret">View/Edit Scores</a>
          </div>
          <div class="menu-item">
            <h2>Reset Scores</h2>
            <p>Clear all score data and logs for a new round.</p>
            <a href="{{ url_for('reset_scores') }}?key=adminsecret">Reset Scores</a>
          </div>
          <div class="menu-item">
            <h2>Generate All QR Codes</h2>
            <p>Generate QR codes for all unique poster assignments.</p>
            <a href="{{ url_for('admin_generate_all_qr') }}?key=adminsecret">Generate All QR</a>
          </div>
          <div class="menu-item">
            <h2>Export Score Matrix</h2>
            <p>Download the score matrix as an XLSX file.</p>
            <a href="{{ url_for('export_score_matrix') }}?key=adminsecret">Export Matrix</a>
          </div>

          <!-- NEW TILE: View Final Results -->
          <div class="menu-item">
            <h2>Upload Results</h2>
            <p>Upload XLSX file with final poster rankings (Poster-ID, Rank).</p>
            <a href="{{ url_for('upload_results') }}?key=adminsecret">Upload Results</a>
          </div>
                  
          <div class="menu-item">
            <h2>Manage Judges & Posters</h2>
            <p>Add, edit, reassign, or delete judges and posters.</p>
            <a href="{{ url_for('admin_manage_judges_posters') }}?key=adminsecret">Manage</a>
          </div>
        </div>
      </div>
    </body>
    </html>
    ''')





@app.route('/generate_qr/<poster_id>')
def generate_qr(poster_id):
    """
    Generates a QR code image for a given poster_id.
    The QR code encodes the URL for the /qr/<poster_id> endpoint.
    """
    # Construct the target URL that judges will be redirected to (i.e., /qr/<poster_id>)
    target_url = url_for('qr_redirect', poster_id=poster_id, _external=True)
    
    # Generate the QR code using the qrcode library
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save image to a BytesIO object and send it as a PNG image
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/admin/upload_results', methods=['GET', 'POST'])
def upload_results():
    """Admin-only route to upload an XLSX file with final poster rankings."""
    # 1. Simple admin check (replace with your own secure method)
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401

    if request.method == 'GET':
        # Show a dark-themed file upload form
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <title>Upload Poster Results</title>
          <link rel="stylesheet"
                href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
          <style>
            body {
              background-color: #121212;
              color: #fff;
              font-family: 'IBM Plex Sans', sans-serif;
              padding: 2rem;
              text-align: center;
            }
            .container {
              max-width: 500px;
              margin: auto;
              background: #1f1f1f;
              padding: 2rem;
              border-radius: 12px;
              box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            input[type="file"] {
              display: block;
              margin: 1rem auto;
              background: #2a2a2a;
              color: #fff;
              border: none;
              padding: 0.5rem;
              border-radius: 8px;
            }
            button {
              padding: 0.5rem 1rem;
              background: #4285F4;
              color: #fff;
              border: none;
              border-radius: 8px;
              cursor: pointer;
              font-size: 1rem;
            }
            button:hover {
              background: #357ae8;
            }
          </style>
        </head>
        <body>
          <div class="container">
            <h2>Upload Poster Results (XLSX)</h2>
            <form method="POST" enctype="multipart/form-data">
              <input type="file" name="file" accept=".xlsx" required>
              <button type="submit">Upload</button>
            </form>
          </div>
        </body>
        </html>
        ''')

    # POST: Process the uploaded XLSX file
    uploaded_file = request.files.get('file')
    if not uploaded_file:
        flash("No file uploaded.")
        return redirect(url_for('upload_results') + "?key=adminsecret")

    try:
        # Parse the XLSX
        wb = openpyxl.load_workbook(uploaded_file)
        sheet = wb.active

        # We expect headers in the first row: Poster-ID, Rank
        # Build a simple dictionary for column indexes
        header_row = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
        try:
            poster_col_idx = header_row.index("Poster-ID")
            rank_col_idx = header_row.index("Rank")
        except ValueError as e:
            return f"Missing required column in header: {str(e)}", 400

        # Clear the old data; parse the new data
        global ranking_data
        ranking_data = []

        for row in sheet.iter_rows(min_row=2):
            poster_id = row[poster_col_idx].value
            rank_val = row[rank_col_idx].value
            if poster_id and rank_val:
                ranking_data.append({
                    "poster_id": str(poster_id).strip(),
                    "rank": int(rank_val)
                })

        # Sort by ascending rank
        ranking_data.sort(key=lambda x: x["rank"])

        # Show a success message with a link to the public results page
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <title>Results Uploaded</title>
          <link rel="stylesheet"
                href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
          <style>
            body {
              background-color: #121212;
              color: #fff;
              font-family: 'IBM Plex Sans', sans-serif;
              text-align: center;
              padding: 2rem;
            }
            .container {
              max-width: 500px;
              margin: auto;
              background: #1f1f1f;
              padding: 2rem;
              border-radius: 12px;
            }
            a.btn {
              display: inline-block;
              margin-top: 1rem;
              padding: 0.5rem 1rem;
              background: #4285F4;
              color: #fff;
              border-radius: 8px;
              text-decoration: none;
            }
            a.btn:hover {
              background: #357ae8;
            }
          </style>
        </head>
        <body>
          <div class="container">
            <h2>Results Uploaded Successfully</h2>
            <p>Your ranking data is now available publicly.</p>
            <a class="btn" href="{{ url_for('view_results', _external=True) }}">View Public Results</a>
          </div>
        </body>
        </html>
        ''')
    except Exception as e:
        return f"Error processing file: {str(e)}", 500



@app.route('/results')
def view_results():
    """
    Publicly viewable route that displays final poster rankings
    in a dark-themed /dashboard style.
    """
    global ranking_data

    if not ranking_data:
        # If no ranking data is uploaded yet, show a placeholder message.
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <title>No Results Yet</title>
        </head>
        <body style="background:#121212;color:white;font-family:sans-serif;text-align:center;padding:2rem;">
          <h2>No rankings available yet.</h2>
        </body>
        </html>
        ''')

    # --- STEP 1: Grab poster titles from DB ---
    db = get_db()
    cur = db.execute("SELECT assigned_poster_titles FROM judges")
    rows = cur.fetchall()

    all_poster_titles = {}  # e.g. {"poster2": "Poster Title #2", "poster5": "Title #5"}
    for row in rows:
        if row['assigned_poster_titles']:
            try:
                titles_dict = json.loads(row['assigned_poster_titles'])
                for pid, title_str in titles_dict.items():
                    all_poster_titles[pid] = title_str
            except Exception:
                pass

    # --- STEP 2: Merge the DB titles into ranking_data. Remove "points". ---
    results = []
    for entry in ranking_data:
        poster_id = entry["poster_id"]  # e.g. "Poster-2"
        rank = entry["rank"]
        # If your DB keys are "poster2" but ranking_data says "Poster-2", unify them:
        db_key = poster_id.replace("Poster-", "poster").lower()
        poster_title = all_poster_titles.get(db_key, "No Title")
        
        results.append({
            "poster_id": poster_id,
            "title": poster_title,
            "rank": rank
        })

    # Sort results by rank ascending
    results.sort(key=lambda x: x["rank"])

    # First 3 are "top3", the rest go below
    top3 = results[:3]
    all_others = results[3:]

    # --- STEP 3: Render a dark-themed “/dashboard” style page. ---
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Poster Rankings</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <!-- Example dashboard-like styling -->
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
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    /* Header / navbar style */
    .header {
      background-color: #1f1f1f;
      padding: 1.5rem;
      border-bottom-left-radius: 24px;
      border-bottom-right-radius: 24px;
      text-align: center;
    }
    .header h1 {
      font-size: 1.8rem;
      font-weight: 600;
      margin-bottom: 0.2rem;
    }
    .header p {
      color: #bbb;
      font-size: 0.9rem;
    }
    /* Main content area */
    .main-content {
      flex: 1;
      padding: 2rem;
    }
    .section-title {
      font-size: 1.3rem;
      font-weight: 600;
      margin-bottom: 1rem;
    }
    .ranking-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .ranking-card {
      background-color: #1f1f1f;
      border-radius: 12px;
      padding: 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    .ranking-left {
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
    }
    .poster-id {
      font-size: 1.1rem;
      font-weight: 600;
      color: #fff;
    }
    .poster-title {
      font-size: 0.85rem;
      color: #ccc;
    }
    .ranking-right {
      font-size: 0.95rem;
      font-weight: 600;
      color: #76c893; /* or #4285F4, whichever you like */
    }
    /* Special icons/colors for top 3 */
    .gold {
      color: #d4af37;
      margin-right: 0.5rem;
      font-size: 1.2rem;
    }
    .silver {
      color: #c0c0c0;
      margin-right: 0.5rem;
      font-size: 1.2rem;
    }
    .bronze {
      color: #cd7f32;
      margin-right: 0.5rem;
      font-size: 1.2rem;
    }
    /* Footer (optional) */
    .footer {
      text-align: center;
      padding: 1rem;
      font-size: 0.8rem;
      background-color: #1f1f1f;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>ECS Poster Results</h1>
    <p>Final Rankings</p>
  </div>

  <div class="main-content">
    <!-- Top 3 -->
    <div class="section-title">Top 3 Posters</div>
    <div class="ranking-list">
      {% for item in top3 %}
        <div class="ranking-card">
          <div class="ranking-left">
            <!-- Use loop.index0 to determine which item (0 -> gold, 1 -> silver, 2 -> bronze) -->
            {% if loop.index0 == 0 %}
              <div>
                <span class="gold">&#x1F3C6;</span>
                <span class="poster-id">{{ item.poster_id }}</span>
              </div>
            {% elif loop.index0 == 1 %}
              <div>
                <span class="silver">2</span>
                <span class="poster-id">{{ item.poster_id }}</span>
              </div>
            {% elif loop.index0 == 2 %}
              <div>
                <span class="bronze">3</span>
                <span class="poster-id">{{ item.poster_id }}</span>
              </div>
            {% endif %}
            <div class="poster-title">{{ item.title }}</div>
          </div>
          <div class="ranking-right">
             {{ item.rank }}
          </div>
        </div>
      {% endfor %}
    </div>

    <!-- All Others -->
    {% if all_others %}
      <div class="section-title" style="margin-top:2rem;">All Other Posters</div>
      <div class="ranking-list">
        {% for item in all_others %}
          <div class="ranking-card">
            <div class="ranking-left">
              <span class="poster-id">{{ item.poster_id }}</span>
              <div class="poster-title">{{ item.title }}</div>
            </div>
            <div class="ranking-right">{{ item.rank }}</div>
          </div>
        {% endfor %}
      </div>
    {% endif %}
  </div>

  <div class="footer">
    ECS Research Day 2025 &mdash; Powered by Flask
  </div>
</body>
</html>
    ''', 
    top3=top3, 
    all_others=all_others
    )

# Judge and poster Management
@app.route('/admin/manage_judges_posters', methods=['GET'])
def admin_manage_judges_posters():
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401
        
    db = get_db()
    judges = db.execute("SELECT email, name, judge_id FROM judge_info ORDER BY name").fetchall()
    
    # Get all unique posters from assignments
    all_posters = set()
    judges_with_posters = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges").fetchall()
    
    for row in judges_with_posters:
        if row['assigned_posters']:
            try:
                posters = json.loads(row['assigned_posters'])
                for poster in posters:
                    all_posters.add(poster)
            except:
                pass
    
    # Convert to list and sort
    poster_list = sorted(list(all_posters), key=lambda p: int(p.replace("poster", "")))
    
    # Get poster titles
    poster_titles = {}
    for row in judges_with_posters:
        if row['assigned_poster_titles']:
            try:
                titles = json.loads(row['assigned_poster_titles'])
                poster_titles.update(titles)
            except:
                pass
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Manage Judges & Posters</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
      <style>
        body {
          background-color: #121212;
          color: #fff;
          font-family: 'IBM Plex Sans', sans-serif;
          padding: 1rem;
        }
        h1 {
          font-size: 1.8rem;
          margin-bottom: 1.5rem;
          text-align: center;
        }
        .container {
          max-width: 900px;
          margin: 0 auto;
        }
        .card {
          background-color: #1f1f1f;
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 2rem;
        }
        .card h2 {
          font-size: 1.4rem;
          margin-bottom: 1rem;
          color: #4285F4;
        }
        .btn {
          background-color: #4285F4;
          color: #fff;
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 8px;
          text-decoration: none;
          cursor: pointer;
          display: inline-block;
          font-size: 0.9rem;
          margin-right: 0.5rem;
          margin-bottom: 0.5rem;
        }
        .btn:hover {
          background-color: #357ae8;
        }
        .btn-danger {
          background-color: #dc3545;
        }
        .btn-danger:hover {
          background-color: #bd2130;
        }
        .btn-success {
          background-color: #28a745;
        }
        .btn-success:hover {
          background-color: #218838;
        }
        .back-link {
          display: block;
          text-align: center;
          margin-top: 2rem;
        }
        .cards-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 1rem;
          margin-top: 1rem;
        }
        .entity-card {
          background-color: #2a2a2a;
          border-radius: 8px;
          padding: 1rem;
        }
        .entity-card h3 {
          font-size: 1.1rem;
          margin-bottom: 0.5rem;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .entity-card p {
          font-size: 0.9rem;
          color: #ccc;
          margin-bottom: 1rem;
        }
        .entity-actions {
          display: flex;
          gap: 0.5rem;
        }
        
        /* Form styles */
        .form-group {
          margin-bottom: 1rem;
        }
        label {
          display: block;
          margin-bottom: 0.3rem;
          font-size: 0.9rem;
          color: #ccc;
        }
        input, select {
          width: 100%;
          padding: 0.5rem;
          border-radius: 4px;
          border: none;
          background-color: #333;
          color: white;
          font-size: 1rem;
        }
        .actions {
          margin-top: 1rem;
          display: flex;
          justify-content: space-between;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>Manage Judges & Posters</h1>
        
        <!-- Quick actions -->
        <div class="card">
          <h2>Quick Actions</h2>
          <a href="{{ url_for('admin_add_judge') }}?key=adminsecret" class="btn btn-success">Add New Judge</a>
          <a href="{{ url_for('admin_add_poster') }}?key=adminsecret" class="btn btn-success">Add New Poster</a>
          <a href="{{ url_for('admin_reassign_poster') }}?key=adminsecret" class="btn">Reassign Poster</a>
          <a href="{{ url_for('admin_export_assignments') }}?key=adminsecret" class="btn">Export Updated Assignments</a>
        </div>
        
        <!-- Judges -->
        <div class="card">
          <h2>Judges</h2>
          <div class="cards-grid">
            {% for judge in judges %}
            <div class="entity-card">
              <h3>{{ judge.name }}</h3>
              <p>{{ judge.email }}</p>
              <div class="entity-actions">
                <a href="{{ url_for('admin_edit_judge', email=judge.email) }}?key=adminsecret" class="btn">Edit</a>
                <a href="{{ url_for('admin_delete_judge', email=judge.email) }}?key=adminsecret" class="btn btn-danger">Delete</a>
              </div>
            </div>
            {% endfor %}
          </div>
        </div>
        
        <!-- Posters -->
        <div class="card">
          <h2>Posters</h2>
          <div class="cards-grid">
            {% for poster_id in poster_list %}
            <div class="entity-card">
              <h3>{{ poster_id }} ({{ poster_id[6:] }})</h3>
              <p>{{ poster_titles.get(poster_id, "No title") }}</p>
              <div class="entity-actions">
                <a href="{{ url_for('admin_edit_poster', poster_id=poster_id) }}?key=adminsecret" class="btn">Edit</a>
                <a href="{{ url_for('admin_delete_poster', poster_id=poster_id) }}?key=adminsecret" class="btn btn-danger">Delete</a>
              </div>
            </div>
            {% endfor %}
          </div>
        </div>
        
        <div class="back-link">
          <a href="{{ url_for('admin_dashboard') }}?key=adminsecret" class="btn">Back to Admin Dashboard</a>
        </div>
      </div>
    </body>
    </html>
    ''', judges=judges, poster_list=poster_list, poster_titles=poster_titles)

@app.route('/admin/add_judge', methods=['GET', 'POST'])
def admin_add_judge():
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401
    
    # Get all existing posters for assignments
    db = get_db()
    all_posters = set()
    poster_titles = {}
    
    judges_with_posters = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges").fetchall()
    for row in judges_with_posters:
        if row['assigned_posters']:
            try:
                posters = json.loads(row['assigned_posters'])
                for poster in posters:
                    all_posters.add(poster)
            except:
                pass
        
        if row['assigned_poster_titles']:
            try:
                titles = json.loads(row['assigned_poster_titles'])
                poster_titles.update(titles)
            except:
                pass
    
    poster_list = sorted(list(all_posters), key=lambda p: int(p.replace("poster", "")))
    
    if request.method == 'POST':
        judge_id = request.form.get('judge_id')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        
        # Validate required fields
        if not all([judge_id, first_name, last_name, email]):
            flash("All fields are required")
            return redirect(url_for('admin_add_judge') + "?key=adminsecret")
        
        # Create full name
        full_name = f"{first_name.strip()} {last_name.strip()}"
        
        # Get assigned posters
        assigned_posters = []
        assigned_poster_titles = {}
        
        for poster_id in poster_list:
            if request.form.get(f'poster_{poster_id}') == 'on':
                assigned_posters.append(poster_id)
                assigned_poster_titles[poster_id] = poster_titles.get(poster_id, "No Title")
        
        db = get_db()
        
        try:
            # Insert into judge_info
            db.execute(
                "INSERT INTO judge_info (judge_id, name, email) VALUES (?, ?, ?)",
                (judge_id, full_name, email)
            )
            
            # Insert into judges
            db.execute(
                "INSERT INTO judges (email, name, assigned_posters, assigned_poster_titles) VALUES (?, ?, ?, ?)",
                (email, full_name, json.dumps(assigned_posters), json.dumps(assigned_poster_titles))
            )
            
            db.commit()
            flash("Judge added successfully")
            return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
        
        except sqlite3.IntegrityError:
            flash("A judge with this email or ID already exists")
            return redirect(url_for('admin_add_judge') + "?key=adminsecret")
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Add New Judge</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
      <style>
        body {
          background-color: #121212;
          color: #fff;
          font-family: 'IBM Plex Sans', sans-serif;
          padding: 1rem;
        }
        .container {
          max-width: 800px;
          margin: 0 auto;
        }
        h1 {
          font-size: 1.8rem;
          margin-bottom: 1.5rem;
          text-align: center;
        }
        .card {
          background-color: #1f1f1f;
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 2rem;
        }
        .form-group {
          margin-bottom: 1rem;
        }
        label {
          display: block;
          margin-bottom: 0.3rem;
          font-size: 0.9rem;
          color: #ccc;
        }
        input, select {
          width: 100%;
          padding: 0.5rem;
          border-radius: 4px;
          border: none;
          background-color: #333;
          color: white;
          font-size: 1rem;
        }
        .btn {
          background-color: #4285F4;
          color: #fff;
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 8px;
          text-decoration: none;
          cursor: pointer;
          display: inline-block;
          font-size: 0.9rem;
          text-align: center;
        }
        .btn:hover {
          background-color: #357ae8;
        }
        .btn-success {
          background-color: #28a745;
        }
        .btn-success:hover {
          background-color: #218838;
        }
        .back-link {
          text-align: center;
          margin-top: 1rem;
        }
        .poster-assignments {
          margin-top: 1.5rem;
          border-top: 1px solid #333;
          padding-top: 1rem;
        }
        .poster-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          gap: 0.8rem;
          margin-top: 0.5rem;
        }
        .poster-item {
          display: flex;
          align-items: center;
          background-color: #2a2a2a;
          border-radius: 6px;
          padding: 0.5rem;
        }
        .poster-item label {
          margin: 0;
          margin-left: 0.5rem;
          cursor: pointer;
        }
        .checkbox {
          width: auto;
        }
        .flash-messages {
          background-color: #f8d7da;
          color: #721c24;
          padding: 0.75rem 1.25rem;
          margin-bottom: 1rem;
          border-radius: 0.25rem;
          text-align: center;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>Add New Judge</h1>
        
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash-messages">
              {% for message in messages %}
                {{ message }}
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        
        <form method="post" class="card">
          <div class="form-group">
            <label for="judge_id">Judge ID:</label>
            <input type="number" id="judge_id" name="judge_id" required>
          </div>
          
          <div class="form-group">
            <label for="first_name">First Name:</label>
            <input type="text" id="first_name" name="first_name" required>
          </div>
          
          <div class="form-group">
            <label for="last_name">Last Name:</label>
            <input type="text" id="last_name" name="last_name" required>
          </div>
          
          <div class="form-group">
            <label for="email">Email:</label>
            <input type="email" id="email" name="email" required>
          </div>
          
          <div class="poster-assignments">
            <h3>Poster Assignments</h3>
            <p style="color: #aaa; margin-bottom: 0.8rem; font-size: 0.9rem;">
              Select posters to assign to this judge:
            </p>
            
            <div class="poster-grid">
              {% for poster_id in poster_list %}
              <div class="poster-item">
                <input type="checkbox" id="poster_{{ poster_id }}" name="poster_{{ poster_id }}" class="checkbox">
                <label for="poster_{{ poster_id }}">
                  {{ poster_id }} ({{ poster_titles.get(poster_id, "No Title") }})
                </label>
              </div>
              {% endfor %}
            </div>
          </div>
          
          <div style="margin-top: 1.5rem;">
            <button type="submit" class="btn btn-success" style="width: 100%;">Add Judge</button>
          </div>
        </form>
        
        <div class="back-link">
          <a href="{{ url_for('admin_manage_judges_posters') }}?key=adminsecret" class="btn">Back to Management</a>
        </div>
      </div>
    </body>
    </html>
    ''', poster_list=poster_list, poster_titles=poster_titles)

@app.route('/admin/add_poster', methods=['GET', 'POST'])
def admin_add_poster():
  if request.args.get('key') != 'adminsecret':
      return "Unauthorized", 401
  
  # Get all judges for possible assignments
  db = get_db()
  judges = db.execute("SELECT email, name FROM judges ORDER BY name").fetchall()
  
  if request.method == 'POST':
      poster_num = request.form.get('poster_num')
      poster_title = request.form.get('poster_title')
      
      if not all([poster_num, poster_title]):
          flash("Poster number and title are required")
          return redirect(url_for('admin_add_poster') + "?key=adminsecret")
      
      # Create poster_id
      poster_id = f"poster{poster_num}"
      
      # Check if this poster already exists
      poster_exists = False
      judges_with_posters = db.execute("SELECT email, assigned_posters FROM judges").fetchall()
      
      for judge in judges_with_posters:
          if judge['assigned_posters']:
              try:
                  assigned_posters = json.loads(judge['assigned_posters'])
                  if poster_id in assigned_posters:
                      poster_exists = True
                      break
              except:
                  pass
      
      if poster_exists:
          flash(f"A poster with ID {poster_id} already exists")
          return redirect(url_for('admin_add_poster') + "?key=adminsecret")
      
      # Get judges to assign this poster to
      selected_judges = []
      for judge in judges:
          if request.form.get(f'judge_{judge["email"]}') == 'on':
              selected_judges.append(judge)
      
      # Update judges table with new poster assignments
      for judge in selected_judges:
          # Get current assignments
          cur = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges WHERE email = ?", 
                        (judge['email'],))
          row = cur.fetchone()
          
          if not row:
              continue
              
          assigned_posters = json.loads(row['assigned_posters']) if row['assigned_posters'] else []
          assigned_titles = json.loads(row['assigned_poster_titles']) if row['assigned_poster_titles'] else {}
          
          # Add new poster
          if poster_id not in assigned_posters:
              assigned_posters.append(poster_id)
              assigned_titles[poster_id] = poster_title
              
              # Update judge record
              db.execute(
                  "UPDATE judges SET assigned_posters = ?, assigned_poster_titles = ? WHERE email = ?",
                  (json.dumps(assigned_posters), json.dumps(assigned_titles), judge['email'])
              )
      
      db.commit()
      flash(f"Poster {poster_id} added successfully")
      return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
  
  return render_template_string('''
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8">
    <title>Add New Poster</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
    <style>
      body {
        background-color: #121212;
        color: #fff;
        font-family: 'IBM Plex Sans', sans-serif;
        padding: 1rem;
      }
      .container {
        max-width: 800px;
        margin: 0 auto;
      }
      h1 {
        font-size: 1.8rem;
        margin-bottom: 1.5rem;
        text-align: center;
      }
      .card {
        background-color: #1f1f1f;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 2rem;
      }
      .form-group {
        margin-bottom: 1rem;
      }
      label {
        display: block;
        margin-bottom: 0.3rem;
        font-size: 0.9rem;
        color: #ccc;
      }
      input, select {
        width: 100%;
        padding: 0.5rem;
        border-radius: 4px;
        border: none;
        background-color: #333;
        color: white;
        font-size: 1rem;
      }
      .btn {
        background-color: #4285F4;
        color: #fff;
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 8px;
        text-decoration: none;
        cursor: pointer;
        display: inline-block;
        font-size: 0.9rem;
        text-align: center;
      }
      .btn:hover {
        background-color: #357ae8;
      }
      .btn-success {
        background-color: #28a745;
      }
      .btn-success:hover {
        background-color: #218838;
      }
      .back-link {
        text-align: center;
        margin-top: 1rem;
      }
      .judge-assignments {
        margin-top: 1.5rem;
        border-top: 1px solid #333;
        padding-top: 1rem;
      }
      .judge-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 0.8rem;
        margin-top: 0.5rem;
      }
      .judge-item {
        display: flex;
        align-items: center;
        background-color: #2a2a2a;
        border-radius: 6px;
        padding: 0.5rem;
      }
      .judge-item label {
        margin: 0;
        margin-left: 0.5rem;
        cursor: pointer;
      }
      .checkbox {
        width: auto;
      }
      .flash-messages {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.75rem 1.25rem;
        margin-bottom: 1rem;
        border-radius: 0.25rem;
        text-align: center;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Add New Poster</h1>
      
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <div class="flash-messages">
            {% for message in messages %}
              {{ message }}
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}
      
      <form method="post" class="card">
        <div class="form-group">
          <label for="poster_num">Poster Number:</label>
          <input type="number" id="poster_num" name="poster_num" required>
          <small style="color: #aaa; display: block; margin-top: 0.3rem;">
            This will be used to create a poster ID like "poster1", "poster2", etc.
          </small>
        </div>
        
        <div class="form-group">
          <label for="poster_title">Poster Title:</label>
          <input type="text" id="poster_title" name="poster_title" required>
        </div>
        
        <div class="judge-assignments">
          <h3>Judge Assignments</h3>
          <p style="color: #aaa; margin-bottom: 0.8rem; font-size: 0.9rem;">
            Select judges to assign to this poster:
          </p>
          
          <div class="judge-grid">
            {% for judge in judges %}
            <div class="judge-item">
              <input type="checkbox" id="judge_{{ judge.email }}" name="judge_{{ judge.email }}" class="checkbox">
              <label for="judge_{{ judge.email }}">
                {{ judge.name }} ({{ judge.email }})
              </label>
            </div>
            {% endfor %}
          </div>
        </div>
        
        <div style="margin-top: 1.5rem;">
          <button type="submit" class="btn btn-success" style="width: 100%;">Add Poster</button>
        </div>
      </form>
      
      <div class="back-link">
        <a href="{{ url_for('admin_manage_judges_posters') }}?key=adminsecret" class="btn">Back to Management</a>
      </div>
    </div>
  </body>
  </html>
  ''', judges=judges)

@app.route('/admin/reassign_poster', methods=['GET', 'POST'])
def admin_reassign_poster():
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401
    
    db = get_db()
    
    # Get all unique posters
    all_posters = set()
    poster_titles = {}
    
    judges_with_posters = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges").fetchall()
    for row in judges_with_posters:
        if row['assigned_posters']:
            try:
                posters = json.loads(row['assigned_posters'])
                for poster in posters:
                    all_posters.add(poster)
            except:
                pass
        
        if row['assigned_poster_titles']:
            try:
                titles = json.loads(row['assigned_poster_titles'])
                poster_titles.update(titles)
            except:
                pass
    
    poster_list = sorted(list(all_posters), key=lambda p: int(p.replace("poster", "")))
    
    # Get all judges
    judges = db.execute("SELECT email, name FROM judges ORDER BY name").fetchall()
    
    if request.method == 'POST':
        poster_id = request.form.get('poster_id')
        target_judge = request.form.get('target_judge')
        source_judge = request.form.get('source_judge')
        
        if not poster_id or not target_judge or not source_judge:
            flash("Please select a poster, source judge, and target judge")
            return redirect(url_for('admin_reassign_poster') + "?key=adminsecret")
        
        # Remove poster from source judge
        cur = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges WHERE email = ?", (source_judge,))
        source_row = cur.fetchone()
        
        if source_row and source_row['assigned_posters']:
            source_posters = json.loads(source_row['assigned_posters'])
            source_titles = json.loads(source_row['assigned_poster_titles']) if source_row['assigned_poster_titles'] else {}
            
            if poster_id in source_posters:
                source_posters.remove(poster_id)
                poster_title = source_titles.get(poster_id, "No Title")
                if poster_id in source_titles:
                    del source_titles[poster_id]
                
                # Update source judge
                db.execute(
                    "UPDATE judges SET assigned_posters = ?, assigned_poster_titles = ? WHERE email = ?",
                    (json.dumps(source_posters), json.dumps(source_titles), source_judge)
                )
                
                # Add poster to target judge
                cur = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges WHERE email = ?", (target_judge,))
                target_row = cur.fetchone()
                
                if target_row:
                    target_posters = json.loads(target_row['assigned_posters']) if target_row['assigned_posters'] else []
                    target_titles = json.loads(target_row['assigned_poster_titles']) if target_row['assigned_poster_titles'] else {}
                    
                    if poster_id not in target_posters:
                        target_posters.append(poster_id)
                        target_titles[poster_id] = poster_title
                        
                        # Update target judge
                        db.execute(
                            "UPDATE judges SET assigned_posters = ?, assigned_poster_titles = ? WHERE email = ?",
                            (json.dumps(target_posters), json.dumps(target_titles), target_judge)
                        )
                
                db.commit()
                flash(f"Poster {poster_id} reassigned successfully")
                return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
            else:
                flash(f"Source judge doesn't have poster {poster_id} assigned")
                return redirect(url_for('admin_reassign_poster') + "?key=adminsecret")
        else:
            flash("Source judge has no posters assigned")
            return redirect(url_for('admin_reassign_poster') + "?key=adminsecret")
    
    # Get judge-poster assignments for dropdown options
    judge_poster_map = {}
    for judge in judges:
        cur = db.execute("SELECT assigned_posters FROM judges WHERE email = ?", (judge['email'],))
        row = cur.fetchone()
        if row and row['assigned_posters']:
            try:
                assigned_posters = json.loads(row['assigned_posters'])
                if assigned_posters:
                    judge_poster_map[judge['email']] = {
                        'name': judge['name'],
                        'posters': assigned_posters
                    }
            except:
                pass
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Reassign Poster</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
      <style>
        body {
          background-color: #121212;
          color: #fff;
          font-family: 'IBM Plex Sans', sans-serif;
          padding: 1rem;
        }
        .container {
          max-width: 800px;
          margin: 0 auto;
        }
        h1 {
          font-size: 1.8rem;
          margin-bottom: 1.5rem;
          text-align: center;
        }
        .card {
          background-color: #1f1f1f;
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 2rem;
        }
        .form-group {
          margin-bottom: 1.5rem;
        }
        label {
          display: block;
          margin-bottom: 0.5rem;
          font-size: 1rem;
          color: #ccc;
        }
        select {
          width: 100%;
          padding: 0.7rem;
          border-radius: 8px;
          border: none;
          background-color: #333;
          color: white;
          font-size: 1rem;
        }
        .btn {
          background-color: #4285F4;
          color: #fff;
          padding: 0.7rem 1rem;
          border: none;
          border-radius: 8px;
          text-decoration: none;
          cursor: pointer;
          display: inline-block;
          font-size: 1rem;
          text-align: center;
        }
        .btn:hover {
          background-color: #357ae8;
        }
        .btn-success {
          background-color: #28a745;
          width: 100%;
          margin-top: 1rem;
          font-size: 1.1rem;
        }
        .btn-success:hover {
          background-color: #218838;
        }
        .back-link {
          text-align: center;
          margin-top: 1rem;
        }
        .flash-messages {
          background-color: #f8d7da;
          color: #721c24;
          padding: 0.75rem 1.25rem;
          margin-bottom: 1rem;
          border-radius: 0.25rem;
          text-align: center;
        }
        .note {
          background-color: #2a2a2a;
          border-radius: 8px;
          padding: 1rem;
          margin-bottom: 1.5rem;
        }
        .note p {
          margin: 0;
          color: #aaa;
          font-size: 0.9rem;
        }
      </style>
      <script>
        function updatePosterOptions() {
          const sourceJudgeSelect = document.getElementById('source_judge');
          const posterSelect = document.getElementById('poster_id');
          const judgeData = JSON.parse(document.getElementById('judge_data').textContent);
          
          // Clear current options
          posterSelect.innerHTML = '<option value="">Select a poster</option>';
          
          const selectedJudge = sourceJudgeSelect.value;
          if (selectedJudge && judgeData[selectedJudge]) {
            const posters = judgeData[selectedJudge].posters;
            const posterTitles = JSON.parse(document.getElementById('poster_titles').textContent);
            
            posters.forEach(posterId => {
              const title = posterTitles[posterId] || 'No Title';
              const option = document.createElement('option');
              option.value = posterId;
              option.textContent = `${posterId} (${title})`;
              posterSelect.appendChild(option);
            });
          }
        }
      </script>
    </head>
    <body>
      <div class="container">
        <h1>Reassign Poster</h1>
        
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash-messages">
              {% for message in messages %}
                {{ message }}
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        
        <div class="note">
          <p>Move a poster from one judge to another. This will update both judges' assignments.</p>
        </div>
        
        <form method="post" class="card">
          <div class="form-group">
            <label for="source_judge">Source Judge (current owner):</label>
            <select id="source_judge" name="source_judge" required onchange="updatePosterOptions()">
              <option value="">Select a judge</option>
              {% for email, data in judge_poster_map.items() %}
                <option value="{{ email }}">{{ data.name }} ({{ email }})</option>
              {% endfor %}
            </select>
          </div>
          
          <div class="form-group">
            <label for="poster_id">Poster to Reassign:</label>
            <select id="poster_id" name="poster_id" required>
              <option value="">Select a poster</option>
              <!-- Options will be populated by JavaScript -->
            </select>
          </div>
          
          <div class="form-group">
            <label for="target_judge">Target Judge (new owner):</label>
            <select id="target_judge" name="target_judge" required>
              <option value="">Select a judge</option>
              {% for judge in judges %}
                <option value="{{ judge.email }}">{{ judge.name }} ({{ judge.email }})</option>
              {% endfor %}
            </select>
          </div>
          
          <button type="submit" class="btn btn-success">Reassign Poster</button>
        </form>
        
        <div class="back-link">
          <a href="{{ url_for('admin_manage_judges_posters') }}?key=adminsecret" class="btn">Back to Management</a>
        </div>
      </div>
      
      <!-- Hidden data for JavaScript -->
      <script id="judge_data" type="application/json">
        {{ judge_poster_map | tojson }}
      </script>
      <script id="poster_titles" type="application/json">
        {{ poster_titles | tojson }}
      </script>
    </body>
    </html>
    ''', judges=judges, poster_list=poster_list, poster_titles=poster_titles, judge_poster_map=judge_poster_map)

@app.route('/admin/export_assignments', methods=['GET'])
def admin_export_assignments():
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401
    
    db = get_db()
    
    # Get all judge data from the database
    judge_info = db.execute("""
        SELECT ji.judge_id, ji.name, ji.email, j.assigned_posters, j.assigned_poster_titles
        FROM judge_info ji
        JOIN judges j ON ji.email = j.email
        ORDER BY ji.judge_id
    """).fetchall()
    
    # Create a new XLSX workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Judge Assignments"
    
    # Set up headers - match format from part_1/output/assignments_extended_judges_with_email copy.xlsx
    headers = ["Judge", "Judge FirstName", "Judge LastName", "Email"]
    
    # Add headers for poster columns (up to poster-6)
    for i in range(1, 7):
        headers.append(f"poster-{i}")
        headers.append(f"poster-{i}-title")
    
    # Write header row
    for col_idx, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_idx, value=header)
    
    # Write data for each judge
    for row_idx, judge in enumerate(judge_info, 2):
        # Split name into first and last name
        name_parts = judge['name'].split(maxsplit=1)
        first_name = name_parts[0] if len(name_parts) > 0 else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Write judge basic info
        ws.cell(row=row_idx, column=1, value=judge['judge_id'])
        ws.cell(row=row_idx, column=2, value=first_name)
        ws.cell(row=row_idx, column=3, value=last_name)
        ws.cell(row=row_idx, column=4, value=judge['email'])
        
        # Get assigned posters and titles
        assigned_posters = json.loads(judge['assigned_posters']) if judge['assigned_posters'] else []
        poster_titles = json.loads(judge['assigned_poster_titles']) if judge['assigned_poster_titles'] else {}
        
        # Write poster assignments (up to 6)
        for i in range(min(len(assigned_posters), 6)):
            poster_id = assigned_posters[i]
            poster_num = int(poster_id.replace("poster", ""))
            
            # Poster columns - each poster has 2 columns (ID and title)
            poster_col = 5 + (i * 2)
            title_col = 6 + (i * 2)
            
            ws.cell(row=row_idx, column=poster_col, value=poster_num)
            ws.cell(row=row_idx, column=title_col, value=poster_titles.get(poster_id, ""))
    
    # Save to a BytesIO stream
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Send file for download
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="assignments_extended_judges_with_email.xlsx"
    )

@app.route('/admin/edit_judge', methods=['GET', 'POST'])
def admin_edit_judge():
    # Fix for malformed URL with two question marks
    key = request.args.get('key')
    
    # If key isn't found, check if email parameter contains the key
    if key != 'adminsecret':
        email = request.args.get('email', '')
        if '?key=adminsecret' in email:
            # Extract the actual email
            request.args = request.args.copy()  # Make args mutable
            request.args['email'] = email.split('?key=')[0]
            key = 'adminsecret'
        else:
            return "Unauthorized", 401
    
    email = request.args.get('email')
    if not email:
        flash("Judge email is required")
        return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
 
    
    db = get_db()
    
    # Get judge info
    cur = db.execute("""
        SELECT ji.judge_id, ji.name, ji.email, j.assigned_posters, j.assigned_poster_titles
        FROM judge_info ji
        JOIN judges j ON ji.email = j.email
        WHERE ji.email = ?
    """, (email,))
    judge = cur.fetchone()
    
    if not judge:
        flash("Judge not found")
        return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
    
    # Get all posters for assignments
    all_posters = set()
    poster_titles = {}
    
    judges_with_posters = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges").fetchall()
    for row in judges_with_posters:
        if row['assigned_posters']:
            try:
                posters = json.loads(row['assigned_posters'])
                for poster in posters:
                    all_posters.add(poster)
            except:
                pass
        
        if row['assigned_poster_titles']:
            try:
                titles = json.loads(row['assigned_poster_titles'])
                poster_titles.update(titles)
            except:
                pass
    
    poster_list = sorted(list(all_posters), key=lambda p: int(p.replace("poster", "")))
    
    # Get assigned posters
    assigned_posters = json.loads(judge['assigned_posters']) if judge['assigned_posters'] else []
    
    if request.method == 'POST':
        judge_id = request.form.get('judge_id')
        name = request.form.get('name')
        new_email = request.form.get('email')
        
        if not all([judge_id, name, new_email]):
            flash("All fields are required")
            return redirect(url_for('admin_edit_judge', email=email) + "?key=adminsecret")
        
        # Check if email is being changed and already exists
        if new_email != email:
            cur = db.execute("SELECT email FROM judges WHERE email = ?", (new_email,))
            if cur.fetchone():
                flash("A judge with this email already exists")
                return redirect(url_for('admin_edit_judge', email=email) + "?key=adminsecret")
        
        # Get updated poster assignments
        updated_posters = []
        updated_titles = {}
        
        for poster_id in poster_list:
            if request.form.get(f'poster_{poster_id}') == 'on':
                updated_posters.append(poster_id)
                updated_titles[poster_id] = poster_titles.get(poster_id, "No Title")
        
        try:
            # Begin transaction
            db.execute("BEGIN TRANSACTION")
            
            # Update judge_info
            db.execute(
                "UPDATE judge_info SET judge_id = ?, name = ?, email = ? WHERE email = ?",
                (judge_id, name, new_email, email)
            )
            
            # Update judges table - if email changed, need to delete old and create new
            if new_email != email:
                db.execute("DELETE FROM judges WHERE email = ?", (email,))
                db.execute(
                    "INSERT INTO judges (email, name, assigned_posters, assigned_poster_titles) VALUES (?, ?, ?, ?)",
                    (new_email, name, json.dumps(updated_posters), json.dumps(updated_titles))
                )
            else:
                db.execute(
                    "UPDATE judges SET name = ?, assigned_posters = ?, assigned_poster_titles = ? WHERE email = ?",
                    (name, json.dumps(updated_posters), json.dumps(updated_titles), email)
                )
            
            # Commit transaction
            db.execute("COMMIT")
            
            flash("Judge updated successfully")
            return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
        
        except Exception as e:
            db.execute("ROLLBACK")
            flash(f"Error updating judge: {str(e)}")
            return redirect(url_for('admin_edit_judge', email=email) + "?key=adminsecret")
    
    # Extract first and last name
    name_parts = judge['name'].split(maxsplit=1)
    first_name = name_parts[0] if len(name_parts) > 0 else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Edit Judge</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
      <style>
        body {
          background-color: #121212;
          color: #fff;
          font-family: 'IBM Plex Sans', sans-serif;
          padding: 1rem;
        }
        .container {
          max-width: 800px;
          margin: 0 auto;
        }
        h1 {
          font-size: 1.8rem;
          margin-bottom: 1.5rem;
          text-align: center;
        }
        .card {
          background-color: #1f1f1f;
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 2rem;
        }
        .form-group {
          margin-bottom: 1rem;
        }
        label {
          display: block;
          margin-bottom: 0.3rem;
          font-size: 0.9rem;
          color: #ccc;
        }
        input, select {
          width: 100%;
          padding: 0.5rem;
          border-radius: 4px;
          border: none;
          background-color: #333;
          color: white;
          font-size: 1rem;
        }
        .btn {
          background-color: #4285F4;
          color: #fff;
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 8px;
          text-decoration: none;
          cursor: pointer;
          display: inline-block;
          font-size: 0.9rem;
          text-align: center;
        }
        .btn:hover {
          background-color: #357ae8;
        }
        .btn-primary {
          background-color: #28a745;
        }
        .btn-primary:hover {
          background-color: #218838;
        }
        .back-link {
          text-align: center;
          margin-top: 1rem;
        }
        .poster-assignments {
          margin-top: 1.5rem;
          border-top: 1px solid #333;
          padding-top: 1rem;
        }
        .poster-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          gap: 0.8rem;
          margin-top: 0.5rem;
        }
        .poster-item {
          display: flex;
          align-items: center;
          background-color: #2a2a2a;
          border-radius: 6px;
          padding: 0.5rem;
        }
        .poster-item label {
          margin: 0;
          margin-left: 0.5rem;
          cursor: pointer;
        }
        .checkbox {
          width: auto;
        }
        .flash-messages {
          background-color: #f8d7da;
          color: #721c24;
          padding: 0.75rem 1.25rem;
          margin-bottom: 1rem;
          border-radius: 0.25rem;
          text-align: center;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>Edit Judge</h1>
        
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash-messages">
              {% for message in messages %}
                {{ message }}
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        
        <form method="post" class="card">
          <div class="form-group">
            <label for="judge_id">Judge ID:</label>
            <input type="number" id="judge_id" name="judge_id" value="{{ judge.judge_id }}" required>
          </div>
          
          <div class="form-group">
            <label for="name">Name:</label>
            <input type="text" id="name" name="name" value="{{ judge.name }}" required>
          </div>
          
          <div class="form-group">
            <label for="email">Email:</label>
            <input type="email" id="email" name="email" value="{{ judge.email }}" required>
          </div>
          
          <div class="poster-assignments">
            <h3>Poster Assignments</h3>
            <p style="color: #aaa; margin-bottom: 0.8rem; font-size: 0.9rem;">
              Select posters to assign to this judge:
            </p>
            
            <div class="poster-grid">
              {% for poster_id in poster_list %}
              <div class="poster-item">
                <input type="checkbox" id="poster_{{ poster_id }}" name="poster_{{ poster_id }}" class="checkbox"
                      {% if poster_id in assigned_posters %}checked{% endif %}>
                <label for="poster_{{ poster_id }}">
                  {{ poster_id }} ({{ poster_titles.get(poster_id, "No Title") }})
                </label>
              </div>
              {% endfor %}
            </div>
          </div>
          
          <div style="margin-top: 1.5rem; display: flex; justify-content: space-between;">
            <a href="{{ url_for('admin_manage_judges_posters') }}?key=adminsecret" class="btn">Cancel</a>
            <button type="submit" class="btn btn-primary">Save Changes</button>
          </div>
        </form>
      </div>
    </body>
    </html>
    ''', judge=judge, poster_list=poster_list, poster_titles=poster_titles, assigned_posters=assigned_posters)


# @app.route('/admin/export_assignments', methods=['GET'])
# def admin_export_assignments():
#     if request.args.get('key') != 'adminsecret':
#         return "Unauthorized", 401
    
#     db = get_db()
    
#     # Get all judge data from the database
#     judge_info = db.execute("""
#         SELECT ji.judge_id, ji.name, ji.email, j.assigned_posters, j.assigned_poster_titles
#         FROM judge_info ji
#         JOIN judges j ON ji.email = j.email
#         ORDER BY ji.judge_id
#     """).fetchall()
    
#     # Create a new XLSX workbook
#     wb = openpyxl.Workbook()
#     ws = wb.active
#     ws.title = "Judge Assignments"
    
#     # Set up headers - match format from part_1/output/assignments_extended_judges_with_email copy.xlsx
#     headers = ["Judge", "Judge FirstName", "Judge LastName", "Email"]
    
#     # Add headers for poster columns (up to poster-6)
#     for i in range(1, 7):
#         headers.append(f"poster-{i}")
#         headers.append(f"poster-{i}-title")
    
#     # Write header row
#     for col_idx, header in enumerate(headers, 1):
#         ws.cell(row=1, column=col_idx, value=header)
    
#     # Write data for each judge
#     for row_idx, judge in enumerate(judge_info, 2):
#         # Split name into first and last name
#         name_parts = judge['name'].split(maxsplit=1)
#         first_name = name_parts[0] if len(name_parts) > 0 else ""
#         last_name = name_parts[1] if len(name_parts) > 1 else ""
        
#         # Write judge basic info
#         ws.cell(row=row_idx, column=1, value=judge['judge_id'])
#         ws.cell(row=row_idx, column=2, value=first_name)
#         ws.cell(row=row_idx, column=3, value=last_name)
#         ws.cell(row=row_idx, column=4, value=judge['email'])
        
#         # Get assigned posters and titles
#         assigned_posters = json.loads(judge['assigned_posters']) if judge['assigned_posters'] else []
#         poster_titles = json.loads(judge['assigned_poster_titles']) if judge['assigned_poster_titles'] else {}
        
#         # Write poster assignments (up to 6)
#         for i in range(min(len(assigned_posters), 6)):
#             poster_id = assigned_posters[i]
#             poster_num = int(poster_id.replace("poster", ""))
            
#             # Poster columns - each poster has 2 columns (ID and title)
#             poster_col = 5 + (i * 2)
#             title_col = 6 + (i * 2)
            
#             ws.cell(row=row_idx, column=poster_col, value=poster_num)
#             ws.cell(row=row_idx, column=title_col, value=poster_titles.get(poster_id, ""))
    
#     # Save to a BytesIO stream
#     output = BytesIO()
#     wb.save(output)
#     output.seek(0)
    
#     # Send file for download
#     return send_file(
#         output,
#         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         as_attachment=True,
#         download_name="assignments_extended_judges_with_email.xlsx"
#     )

# @app.route('/admin/edit_judge', methods=['GET', 'POST'])
# def admin_edit_judge():
#     if request.args.get('key') != 'adminsecret':
#         return "Unauthorized", 401
    
#     email = request.args.get('email')
#     if not email:
#         flash("Judge email is required")
#         return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
    
#     db = get_db()
    
#     # Get judge info
#     cur = db.execute("""
#         SELECT ji.judge_id, ji.name, ji.email, j.assigned_posters, j.assigned_poster_titles
#         FROM judge_info ji
#         JOIN judges j ON ji.email = j.email
#         WHERE ji.email = ?
#     """, (email,))
#     judge = cur.fetchone()
    
#     if not judge:
#         flash("Judge not found")
#         return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
    
#     # Get all posters for assignments
#     all_posters = set()
#     poster_titles = {}
    
#     judges_with_posters = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges").fetchall()
#     for row in judges_with_posters:
#         if row['assigned_posters']:
#             try:
#                 posters = json.loads(row['assigned_posters'])
#                 for poster in posters:
#                     all_posters.add(poster)
#             except:
#                 pass
        
#         if row['assigned_poster_titles']:
#             try:
#                 titles = json.loads(row['assigned_poster_titles'])
#                 poster_titles.update(titles)
#             except:
#                 pass
    
#     poster_list = sorted(list(all_posters), key=lambda p: int(p.replace("poster", "")))
    
#     # Get assigned posters
#     assigned_posters = json.loads(judge['assigned_posters']) if judge['assigned_posters'] else []
    
#     if request.method == 'POST':
#         judge_id = request.form.get('judge_id')
#         name = request.form.get('name')
#         new_email = request.form.get('email')
        
#         if not all([judge_id, name, new_email]):
#             flash("All fields are required")
#             return redirect(url_for('admin_edit_judge', email=email) + "?key=adminsecret")
        
#         # Check if email is being changed and already exists
#         if new_email != email:
#             cur = db.execute("SELECT email FROM judges WHERE email = ?", (new_email,))
#             if cur.fetchone():
#                 flash("A judge with this email already exists")
#                 return redirect(url_for('admin_edit_judge', email=email) + "?key=adminsecret")
        
#         # Get updated poster assignments
#         updated_posters = []
#         updated_titles = {}
        
#         for poster_id in poster_list:
#             if request.form.get(f'poster_{poster_id}') == 'on':
#                 updated_posters.append(poster_id)
#                 updated_titles[poster_id] = poster_titles.get(poster_id, "No Title")
        
#         try:
#             # Begin transaction
#             db.execute("BEGIN TRANSACTION")
            
#             # Update judge_info
#             db.execute(
#                 "UPDATE judge_info SET judge_id = ?, name = ?, email = ? WHERE email = ?",
#                 (judge_id, name, new_email, email)
#             )
            
#             # Update judges table - if email changed, need to delete old and create new
#             if new_email != email:
#                 db.execute("DELETE FROM judges WHERE email = ?", (email,))
#                 db.execute(
#                     "INSERT INTO judges (email, name, assigned_posters, assigned_poster_titles) VALUES (?, ?, ?, ?)",
#                     (new_email, name, json.dumps(updated_posters), json.dumps(updated_titles))
#                 )
#             else:
#                 db.execute(
#                     "UPDATE judges SET name = ?, assigned_posters = ?, assigned_poster_titles = ? WHERE email = ?",
#                     (name, json.dumps(updated_posters), json.dumps(updated_titles), email)
#                 )
            
#             # Commit transaction
#             db.execute("COMMIT")
            
#             flash("Judge updated successfully")
#             return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
        
#         except Exception as e:
#             db.execute("ROLLBACK")
#             flash(f"Error updating judge: {str(e)}")
#             return redirect(url_for('admin_edit_judge', email=email) + "?key=adminsecret")
    
#     # Extract first and last name
#     name_parts = judge['name'].split(maxsplit=1)
#     first_name = name_parts[0] if len(name_parts) > 0 else ""
#     last_name = name_parts[1] if len(name_parts) > 1 else ""
    
#     return render_template_string('''
#     <!DOCTYPE html>
#     <html lang="en">
#     <head>
#       <meta charset="UTF-8">
#       <title>Edit Judge</title>
#       <meta name="viewport" content="width=device-width, initial-scale=1.0">
#       <link rel="stylesheet"
#             href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
#       <style>
#         body {
#           background-color: #121212;
#           color: #fff;
#           font-family: 'IBM Plex Sans', sans-serif;
#           padding: 1rem;
#         }
#         .container {
#           max-width: 800px;
#           margin: 0 auto;
#         }
#         h1 {
#           font-size: 1.8rem;
#           margin-bottom: 1.5rem;
#           text-align: center;
#         }
#         .card {
#           background-color: #1f1f1f;
#           border-radius: 12px;
#           padding: 1.5rem;
#           margin-bottom: 2rem;
#         }
#         .form-group {
#           margin-bottom: 1rem;
#         }
#         label {
#           display: block;
#           margin-bottom: 0.3rem;
#           font-size: 0.9rem;
#           color: #ccc;
#         }
#         input, select {
#           width: 100%;
#           padding: 0.5rem;
#           border-radius: 4px;
#           border: none;
#           background-color: #333;
#           color: white;
#           font-size: 1rem;
#         }
#         .btn {
#           background-color: #4285F4;
#           color: #fff;
#           padding: 0.5rem 1rem;
#           border: none;
#           border-radius: 8px;
#           text-decoration: none;
#           cursor: pointer;
#           display: inline-block;
#           font-size: 0.9rem;
#           text-align: center;
#         }
#         .btn:hover {
#           background-color: #357ae8;
#         }
#         .btn-primary {
#           background-color: #28a745;
#         }
#         .btn-primary:hover {
#           background-color: #218838;
#         }
#         .back-link {
#           text-align: center;
#           margin-top: 1rem;
#         }
#         .poster-assignments {
#           margin-top: 1.5rem;
#           border-top: 1px solid #333;
#           padding-top: 1rem;
#         }
#         .poster-grid {
#           display: grid;
#           grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
#           gap: 0.8rem;
#           margin-top: 0.5rem;
#         }
#         .poster-item {
#           display: flex;
#           align-items: center;
#           background-color: #2a2a2a;
#           border-radius: 6px;
#           padding: 0.5rem;
#         }
#         .poster-item label {
#           margin: 0;
#           margin-left: 0.5rem;
#           cursor: pointer;
#         }
#         .checkbox {
#           width: auto;
#         }
#         .flash-messages {
#           background-color: #f8d7da;
#           color: #721c24;
#           padding: 0.75rem 1.25rem;
#           margin-bottom: 1rem;
#           border-radius: 0.25rem;
#           text-align: center;
#         }
#       </style>
#     </head>
#     <body>
#       <div class="container">
#         <h1>Edit Judge</h1>
        
#         {% with messages = get_flashed_messages() %}
#           {% if messages %}
#             <div class="flash-messages">
#               {% for message in messages %}
#                 {{ message }}
#               {% endfor %}
#             </div>
#           {% endif %}
#         {% endwith %}
        
#         <form method="post" class="card">
#           <div class="form-group">
#             <label for="judge_id">Judge ID:</label>
#             <input type="number" id="judge_id" name="judge_id" value="{{ judge.judge_id }}" required>
#           </div>
          
#           <div class="form-group">
#             <label for="name">Name:</label>
#             <input type="text" id="name" name="name" value="{{ judge.name }}" required>
#           </div>
          
#           <div class="form-group">
#             <label for="email">Email:</label>
#             <input type="email" id="email" name="email" value="{{ judge.email }}" required>
#           </div>
          
#           <div class="poster-assignments">
#             <h3>Poster Assignments</h3>
#             <p style="color: #aaa; margin-bottom: 0.8rem; font-size: 0.9rem;">
#               Select posters to assign to this judge:
#             </p>
            
#             <div class="poster-grid">
#               {% for poster_id in poster_list %}
#               <div class="poster-item">
#                 <input type="checkbox" id="poster_{{ poster_id }}" name="poster_{{ poster_id }}" class="checkbox"
#                       {% if poster_id in assigned_posters %}checked{% endif %}>
#                 <label for="poster_{{ poster_id }}">
#                   {{ poster_id }} ({{ poster_titles.get(poster_id, "No Title") }})
#                 </label>
#               </div>
#               {% endfor %}
#             </div>
#           </div>
          
#           <div style="margin-top: 1.5rem; display: flex; justify-content: space-between;">
#             <a href="{{ url_for('admin_manage_judges_posters') }}?key=adminsecret" class="btn">Cancel</a>
#             <button type="submit" class="btn btn-primary">Save Changes</button>
#           </div>
#         </form>
#       </div>
#     </body>
#     </html>
#     ''', judge=judge, poster_list=poster_list, poster_titles=poster_titles, assigned_posters=assigned_posters)



def admin_reassign_poster():
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401
    
    db = get_db()
    
    # Get all unique posters
    all_posters = set()
    poster_titles = {}
    
    judges_with_posters = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges").fetchall()
    for row in judges_with_posters:
        if row['assigned_posters']:
            try:
                posters = json.loads(row['assigned_posters'])
                for poster in posters:
                    all_posters.add(poster)
            except:
                pass
        
        if row['assigned_poster_titles']:
            try:
                titles = json.loads(row['assigned_poster_titles'])
                poster_titles.update(titles)
            except:
                pass
    
    poster_list = sorted(list(all_posters), key=lambda p: int(p.replace("poster", "")))
    
    # Get all judges
    judges = db.execute("SELECT email, name FROM judges ORDER BY name").fetchall()
    
    if request.method == 'POST':
        poster_id = request.form.get('poster_id')
        target_judge = request.form.get('target_judge')
        source_judge = request.form.get('source_judge')
        
        if not poster_id or not target_judge or not source_judge:
            flash("Please select a poster, source judge, and target judge")
            return redirect(url_for('admin_reassign_poster') + "?key=adminsecret")
        
        # Remove poster from source judge
        cur = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges WHERE email = ?", (source_judge,))
        source_row = cur.fetchone()
        
        if source_row and source_row['assigned_posters']:
            source_posters = json.loads(source_row['assigned_posters'])
            source_titles = json.loads(source_row['assigned_poster_titles']) if source_row['assigned_poster_titles'] else {}
            
            if poster_id in source_posters:
                source_posters.remove(poster_id)
                poster_title = source_titles.get(poster_id, "No Title")
                if poster_id in source_titles:
                    del source_titles[poster_id]
                
                # Update source judge
                db.execute(
                    "UPDATE judges SET assigned_posters = ?, assigned_poster_titles = ? WHERE email = ?",
                    (json.dumps(source_posters), json.dumps(source_titles), source_judge)
                )
                
                # Add poster to target judge
                cur = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges WHERE email = ?", (target_judge,))
                target_row = cur.fetchone()
                
                if target_row:
                    target_posters = json.loads(target_row['assigned_posters']) if target_row['assigned_posters'] else []
                    target_titles = json.loads(target_row['assigned_poster_titles']) if target_row['assigned_poster_titles'] else {}
                    
                    if poster_id not in target_posters:
                        target_posters.append(poster_id)
                        target_titles[poster_id] = poster_title
                        
                        # Update target judge
                        db.execute(
                            "UPDATE judges SET assigned_posters = ?, assigned_poster_titles = ? WHERE email = ?",
                            (json.dumps(target_posters), json.dumps(target_titles), target_judge)
                        )
                
                db.commit()
                flash(f"Poster {poster_id} reassigned successfully")
                return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
            else:
                flash(f"Source judge doesn't have poster {poster_id} assigned")
                return redirect(url_for('admin_reassign_poster') + "?key=adminsecret")
        else:
            flash("Source judge has no posters assigned")
            return redirect(url_for('admin_reassign_poster') + "?key=adminsecret")
    
    # Get judge-poster assignments for dropdown options
    judge_poster_map = {}
    for judge in judges:
        cur = db.execute("SELECT assigned_posters FROM judges WHERE email = ?", (judge['email'],))
        row = cur.fetchone()
        if row and row['assigned_posters']:
            try:
                assigned_posters = json.loads(row['assigned_posters'])
                if assigned_posters:
                    judge_poster_map[judge['email']] = {
                        'name': judge['name'],
                        'posters': assigned_posters
                    }
            except:
                pass
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Reassign Poster</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
      <style>
        body {
          background-color: #121212;
          color: #fff;
          font-family: 'IBM Plex Sans', sans-serif;
          padding: 1rem;
        }
        .container {
          max-width: 800px;
          margin: 0 auto;
        }
        h1 {
          font-size: 1.8rem;
          margin-bottom: 1.5rem;
          text-align: center;
        }
        .card {
          background-color: #1f1f1f;
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 2rem;
        }
        .form-group {
          margin-bottom: 1.5rem;
        }
        label {
          display: block;
          margin-bottom: 0.5rem;
          font-size: 1rem;
          color: #ccc;
        }
        select {
          width: 100%;
          padding: 0.7rem;
          border-radius: 8px;
          border: none;
          background-color: #333;
          color: white;
          font-size: 1rem;
        }
        .btn {
          background-color: #4285F4;
          color: #fff;
          padding: 0.7rem 1rem;
          border: none;
          border-radius: 8px;
          text-decoration: none;
          cursor: pointer;
          display: inline-block;
          font-size: 1rem;
          text-align: center;
        }
        .btn:hover {
          background-color: #357ae8;
        }
        .btn-success {
          background-color: #28a745;
          width: 100%;
          margin-top: 1rem;
          font-size: 1.1rem;
        }
        .btn-success:hover {
          background-color: #218838;
        }
        .back-link {
          text-align: center;
          margin-top: 1rem;
        }
        .flash-messages {
          background-color: #f8d7da;
          color: #721c24;
          padding: 0.75rem 1.25rem;
          margin-bottom: 1rem;
          border-radius: 0.25rem;
          text-align: center;
        }
        .note {
          background-color: #2a2a2a;
          border-radius: 8px;
          padding: 1rem;
          margin-bottom: 1.5rem;
        }
        .note p {
          margin: 0;
          color: #aaa;
          font-size: 0.9rem;
        }
      </style>
      <script>
        function updatePosterOptions() {
          const sourceJudgeSelect = document.getElementById('source_judge');
          const posterSelect = document.getElementById('poster_id');
          const judgeData = JSON.parse(document.getElementById('judge_data').textContent);
          
          // Clear current options
          posterSelect.innerHTML = '<option value="">Select a poster</option>';
          
          const selectedJudge = sourceJudgeSelect.value;
          if (selectedJudge && judgeData[selectedJudge]) {
            const posters = judgeData[selectedJudge].posters;
            const posterTitles = JSON.parse(document.getElementById('poster_titles').textContent);
            
            posters.forEach(posterId => {
              const title = posterTitles[posterId] || 'No Title';
              const option = document.createElement('option');
              option.value = posterId;
              option.textContent = `${posterId} (${title})`;
              posterSelect.appendChild(option);
            });
          }
        }
      </script>
    </head>
    <body>
      <div class="container">
        <h1>Reassign Poster</h1>
        
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash-messages">
              {% for message in messages %}
                {{ message }}
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        
        <div class="note">
          <p>Move a poster from one judge to another. This will update both judges' assignments.</p>
        </div>
        
        <form method="post" class="card">
          <div class="form-group">
            <label for="source_judge">Source Judge (current owner):</label>
            <select id="source_judge" name="source_judge" required onchange="updatePosterOptions()">
              <option value="">Select a judge</option>
              {% for email, data in judge_poster_map.items() %}
                <option value="{{ email }}">{{ data.name }} ({{ email }})</option>
              {% endfor %}
            </select>
          </div>
          
          <div class="form-group">
            <label for="poster_id">Poster to Reassign:</label>
            <select id="poster_id" name="poster_id" required>
              <option value="">Select a poster</option>
              <!-- Options will be populated by JavaScript -->
            </select>
          </div>
          
          <div class="form-group">
            <label for="target_judge">Target Judge (new owner):</label>
            <select id="target_judge" name="target_judge" required>
              <option value="">Select a judge</option>
              {% for judge in judges %}
                <option value="{{ judge.email }}">{{ judge.name }} ({{ judge.email }})</option>
              {% endfor %}
            </select>
          </div>
          
          <button type="submit" class="btn btn-success">Reassign Poster</button>
        </form>
        
        <div class="back-link">
          <a href="{{ url_for('admin_manage_judges_posters') }}?key=adminsecret" class="btn">Back to Management</a>
        </div>
      </div>
      
      <!-- Hidden data for JavaScript -->
      <script id="judge_data" type="application/json">
        {{ judge_poster_map | tojson }}
      </script>
      <script id="poster_titles" type="application/json">
        {{ poster_titles | tojson }}
      </script>
    </body>
    </html>
    ''', judges=judges, poster_list=poster_list, poster_titles=poster_titles, judge_poster_map=judge_poster_map)

@app.route('/admin/delete_judge', methods=['GET', 'POST'])
def admin_delete_judge():
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401
    
    email = request.args.get('email')
    if not email:
        flash("Judge email is required")
        return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
    
    db = get_db()
    
    # Get judge info
    cur = db.execute("SELECT name FROM judges WHERE email = ?", (email,))
    judge = cur.fetchone()
    
    if not judge:
        flash("Judge not found")
        return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
    
    if request.method == 'POST':
        try:
            # Begin transaction
            db.execute("BEGIN TRANSACTION")
            
            # Delete from judge_info and judges tables
            db.execute("DELETE FROM judge_info WHERE email = ?", (email,))
            db.execute("DELETE FROM judges WHERE email = ?", (email,))
            
            # Delete any scores submitted by this judge
            db.execute("DELETE FROM scores WHERE judge_email = ?", (email,))
            db.execute("DELETE FROM score_changes WHERE judge_email = ? OR judge_email LIKE ?", 
                    (email, f"{email} [ADMIN]"))
            
            # Commit transaction
            db.execute("COMMIT")
            
            flash(f"Judge {judge['name']} has been deleted")
            return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
        
        except Exception as e:
            db.execute("ROLLBACK")
            flash(f"Error deleting judge: {str(e)}")
            return redirect(url_for('admin_delete_judge', email=email) + "?key=adminsecret")
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Delete Judge</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
      <style>
        body {
          background-color: #121212;
          color: #fff;
          font-family: 'IBM Plex Sans', sans-serif;
          padding: 1rem;
        }
        .container {
          max-width: 500px;
          margin: 0 auto;
          text-align: center;
        }
        h1 {
          font-size: 1.8rem;
          margin-bottom: 1rem;
        }
        .card {
          background-color: #1f1f1f;
          border-radius: 12px;
          padding: 2rem;
          margin: 2rem 0;
        }
        .warning {
          color: #ff6b6b;
          margin-bottom: 1.5rem;
          font-weight: bold;
        }
        .details {
          margin-bottom: 2rem;
          color: #ccc;
        }
        .btn {
          display: inline-block;
          padding: 0.7rem 1.5rem;
          border-radius: 8px;
          text-decoration: none;
          cursor: pointer;
          font-size: 1rem;
          margin: 0 0.5rem;
        }
        .btn-danger {
          background-color: #dc3545;
          color: white;
          border: none;
        }
        .btn-danger:hover {
          background-color: #bd2130;
        }
        .btn-secondary {
          background-color: #6c757d;
          color: white;
        }
        .btn-secondary:hover {
          background-color: #5a6268;
        }
        .flash-messages {
          background-color: #f8d7da;
          color: #721c24;
          padding: 0.75rem 1.25rem;
          margin-bottom: 1rem;
          border-radius: 0.25rem;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>Delete Judge</h1>
        
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash-messages">
              {% for message in messages %}
                {{ message }}
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        
        <div class="card">
          <p class="warning">Warning: This action cannot be undone!</p>
          
          <div class="details">
            <p>You are about to delete the following judge:</p>
            <h2>{{ judge.name }}</h2>
            <p>{{ email }}</p>
            <p>This will also remove all scores submitted by this judge.</p>
          </div>
          
          <form method="post">
            <a href="{{ url_for('admin_manage_judges_posters') }}?key=adminsecret" class="btn btn-secondary">Cancel</a>
            <button type="submit" class="btn btn-danger">Confirm Delete</button>
          </form>
        </div>
      </div>
    </body>
    </html>
    ''', judge=judge, email=email)


@app.route('/admin/edit_poster', methods=['GET', 'POST'])
def admin_edit_poster():
    # Fix for malformed URL with two question marks
    key = request.args.get('key')
    
    # If key isn't found, check if poster_id parameter contains the key
    if key != 'adminsecret':
        poster_id = request.args.get('poster_id', '')
        if '?key=adminsecret' in poster_id:
            # Extract the actual poster_id
            request.args = request.args.copy()  # Make args mutable
            request.args['poster_id'] = poster_id.split('?key=')[0]
            key = 'adminsecret'
        else:
            return "Unauthorized", 401
    
    poster_id = request.args.get('poster_id')
    if not poster_id:
        flash("Poster ID is required")
        return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
   
    
    db = get_db()
    
    # Get poster title from any judge that has it
    cur = db.execute("SELECT assigned_poster_titles FROM judges WHERE assigned_poster_titles LIKE ?", 
                    (f'%"{poster_id}"%',))
    poster_title = None
    
    for row in cur.fetchall():
        if row['assigned_poster_titles']:
            try:
                titles = json.loads(row['assigned_poster_titles'])
                if poster_id in titles:
                    poster_title = titles[poster_id]
                    break
            except:
                pass
    
    if poster_title is None:
        flash(f"Poster {poster_id} not found")
        return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
    
    # Get all judges
    judges = db.execute("SELECT email, name FROM judges ORDER BY name").fetchall()
    
    # Get which judges this poster is assigned to
    assigned_judges = []
    
    for judge in judges:
        cur = db.execute("SELECT assigned_posters FROM judges WHERE email = ?", (judge['email'],))
        row = cur.fetchone()
        
        if row and row['assigned_posters']:
            try:
                posters = json.loads(row['assigned_posters'])
                if poster_id in posters:
                    assigned_judges.append(judge['email'])
            except:
                pass
    
    if request.method == 'POST':
        new_title = request.form.get('title')
        
        if not new_title:
            flash("Poster title is required")
            return redirect(url_for('admin_edit_poster', poster_id=poster_id) + "?key=adminsecret")
        
        # Get the judge assignments
        updated_judges = []
        
        for judge in judges:
            if request.form.get(f'judge_{judge["email"]}') == 'on':
                updated_judges.append(judge['email'])
        
        try:
            # Begin transaction
            db.execute("BEGIN TRANSACTION")
            
            # Update poster title and assignments for all judges
            for judge in judges:
                cur = db.execute("SELECT assigned_posters, assigned_poster_titles FROM judges WHERE email = ?", 
                              (judge['email'],))
                row = cur.fetchone()
                
                if not row:
                    continue
                
                assigned_posters = json.loads(row['assigned_posters']) if row['assigned_posters'] else []
                assigned_titles = json.loads(row['assigned_poster_titles']) if row['assigned_poster_titles'] else {}
                
                # Determine if this judge should have the poster
                should_have_poster = judge['email'] in updated_judges
                has_poster = poster_id in assigned_posters
                
                if should_have_poster and not has_poster:
                    # Add poster to this judge
                    assigned_posters.append(poster_id)
                    assigned_titles[poster_id] = new_title
                    db.execute(
                        "UPDATE judges SET assigned_posters = ?, assigned_poster_titles = ? WHERE email = ?",
                        (json.dumps(assigned_posters), json.dumps(assigned_titles), judge['email'])
                    )
                elif not should_have_poster and has_poster:
                    # Remove poster from this judge
                    assigned_posters.remove(poster_id)
                    if poster_id in assigned_titles:
                        del assigned_titles[poster_id]
                    db.execute(
                        "UPDATE judges SET assigned_posters = ?, assigned_poster_titles = ? WHERE email = ?",
                        (json.dumps(assigned_posters), json.dumps(assigned_titles), judge['email'])
                    )
                elif should_have_poster and has_poster:
                    # Just update the title
                    assigned_titles[poster_id] = new_title
                    db.execute(
                        "UPDATE judges SET assigned_poster_titles = ? WHERE email = ?",
                        (json.dumps(assigned_titles), judge['email'])
                    )
            
            # Commit transaction
            db.execute("COMMIT")
            
            flash(f"Poster {poster_id} updated successfully")
            return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
        
        except Exception as e:
            db.execute("ROLLBACK")
            flash(f"Error updating poster: {str(e)}")
            return redirect(url_for('admin_edit_poster', poster_id=poster_id) + "?key=adminsecret")
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Edit Poster</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
      <style>
        body {
          background-color: #121212;
          color: #fff;
          font-family: 'IBM Plex Sans', sans-serif;
          padding: 1rem;
        }
        .container {
          max-width: 800px;
          margin: 0 auto;
        }
        h1 {
          font-size: 1.8rem;
          margin-bottom: 1.5rem;
          text-align: center;
        }
        .card {
          background-color: #1f1f1f;
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 2rem;
        }
        .form-group {
          margin-bottom: 1rem;
        }
        label {
          display: block;
          margin-bottom: 0.3rem;
          font-size: 0.9rem;
          color: #ccc;
        }
        input, select {
          width: 100%;
          padding: 0.5rem;
          border-radius: 4px;
          border: none;
          background-color: #333;
          color: white;
          font-size: 1rem;
        }
        .btn {
          background-color: #4285F4;
          color: #fff;
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 8px;
          text-decoration: none;
          cursor: pointer;
          display: inline-block;
          font-size: 0.9rem;
          text-align: center;
        }
        .btn:hover {
          background-color: #357ae8;
        }
        .btn-primary {
          background-color: #28a745;
        }
        .btn-primary:hover {
          background-color: #218838;
        }
        .back-link {
          text-align: center;
          margin-top: 1rem;
        }
        .judge-assignments {
          margin-top: 1.5rem;
          border-top: 1px solid #333;
          padding-top: 1rem;
        }
        .judge-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
          gap: 0.8rem;
          margin-top: 0.5rem;
        }
        .judge-item {
          display: flex;
          align-items: center;
          background-color: #2a2a2a;
          border-radius: 6px;
          padding: 0.5rem;
        }
        .judge-item label {
          margin: 0;
          margin-left: 0.5rem;
          cursor: pointer;
        }
        .checkbox {
          width: auto;
        }
        .flash-messages {
          background-color: #f8d7da;
          color: #721c24;
          padding: 0.75rem 1.25rem;
          margin-bottom: 1rem;
          border-radius: 0.25rem;
          text-align: center;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>Edit Poster</h1>
        
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash-messages">
              {% for message in messages %}
                {{ message }}
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        
        <form method="post" class="card">
          <div class="form-group">
            <label for="poster_id">Poster ID:</label>
            <input type="text" id="poster_id" value="{{ poster_id }}" readonly>
          </div>
          
          <div class="form-group">
            <label for="title">Title:</label>
            <input type="text" id="title" name="title" value="{{ poster_title }}" required>
          </div>
          
          <div class="judge-assignments">
            <h3>Judge Assignments</h3>
            <p style="color: #aaa; margin-bottom: 0.8rem; font-size: 0.9rem;">
              Select judges to assign to this poster:
            </p>
            
            <div class="judge-grid">
              {% for judge in judges %}
              <div class="judge-item">
                <input type="checkbox" id="judge_{{ judge.email }}" name="judge_{{ judge.email }}" class="checkbox"
                      {% if judge.email in assigned_judges %}checked{% endif %}>
                <label for="judge_{{ judge.email }}">
                  {{ judge.name }} ({{ judge.email }})
                </label>
              </div>
              {% endfor %}
            </div>
          </div>
          
          <div style="margin-top: 1.5rem; display: flex; justify-content: space-between;">
            <a href="{{ url_for('admin_manage_judges_posters') }}?key=adminsecret" class="btn">Cancel</a>
            <button type="submit" class="btn btn-primary">Save Changes</button>
          </div>
        </form>
      </div>
    </body>
    </html>
    ''', poster_id=poster_id, poster_title=poster_title, judges=judges, assigned_judges=assigned_judges)


@app.route('/admin/delete_poster', methods=['GET', 'POST'])
def admin_delete_poster():
    if request.args.get('key') != 'adminsecret':
        return "Unauthorized", 401
    
    poster_id = request.args.get('poster_id')
    if not poster_id:
        flash("Poster ID is required")
        return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
    
    db = get_db()
    
    # Get poster title from any judge that has it
    cur = db.execute("SELECT assigned_poster_titles FROM judges WHERE assigned_poster_titles LIKE ?", 
                  (f'%"{poster_id}"%',))
    poster_title = None
    
    for row in cur.fetchall():
        if row['assigned_poster_titles']:
            try:
                titles = json.loads(row['assigned_poster_titles'])
                if poster_id in titles:
                    poster_title = titles[poster_id]
                    break
            except:
                pass
    
    if poster_title is None:
        flash(f"Poster {poster_id} not found")
        return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
    
    if request.method == 'POST':
        try:
            # Begin transaction
            db.execute("BEGIN TRANSACTION")
            
            # Remove this poster from all judges
            judges = db.execute("SELECT email, assigned_posters, assigned_poster_titles FROM judges").fetchall()
            
            for judge in judges:
                if judge['assigned_posters']:
                    try:
                        assigned_posters = json.loads(judge['assigned_posters'])
                        assigned_titles = json.loads(judge['assigned_poster_titles']) if judge['assigned_poster_titles'] else {}
                        
                        if poster_id in assigned_posters:
                            assigned_posters.remove(poster_id)
                            if poster_id in assigned_titles:
                                del assigned_titles[poster_id]
                            
                            db.execute(
                                "UPDATE judges SET assigned_posters = ?, assigned_poster_titles = ? WHERE email = ?",
                                (json.dumps(assigned_posters), json.dumps(assigned_titles), judge['email'])
                            )
                    except:
                        pass
            
            # Delete any scores for this poster
            db.execute("DELETE FROM scores WHERE poster_id = ?", (poster_id,))
            db.execute("DELETE FROM score_changes WHERE poster_id = ?", (poster_id,))
            
            # Commit transaction
            db.execute("COMMIT")
            
            flash(f"Poster {poster_id} has been deleted")
            return redirect(url_for('admin_manage_judges_posters') + "?key=adminsecret")
        
        except Exception as e:
            db.execute("ROLLBACK")
            flash(f"Error deleting poster: {str(e)}")
            return redirect(url_for('admin_delete_poster', poster_id=poster_id) + "?key=adminsecret")
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Delete Poster</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap">
      <style>
        body {
          background-color: #121212;
          color: #fff;
          font-family: 'IBM Plex Sans', sans-serif;
          padding: 1rem;
        }
        .container {
          max-width: 500px;
          margin: 0 auto;
          text-align: center;
        }
        h1 {
          font-size: 1.8rem;
          margin-bottom: 1rem;
        }
        .card {
          background-color: #1f1f1f;
          border-radius: 12px;
          padding: 2rem;
          margin: 2rem 0;
        }
        .warning {
          color: #ff6b6b;
          margin-bottom: 1.5rem;
          font-weight: bold;
        }
        .details {
          margin-bottom: 2rem;
          color: #ccc;
        }
        .btn {
          display: inline-block;
          padding: 0.7rem 1.5rem;
          border-radius: 8px;
          text-decoration: none;
          cursor: pointer;
          font-size: 1rem;
          margin: 0 0.5rem;
        }
        .btn-danger {
          background-color: #dc3545;
          color: white;
          border: none;
        }
        .btn-danger:hover {
          background-color: #bd2130;
        }
        .btn-secondary {
          background-color: #6c757d;
          color: white;
        }
        .btn-secondary:hover {
          background-color: #5a6268;
        }
        .flash-messages {
          background-color: #f8d7da;
          color: #721c24;
          padding: 0.75rem 1.25rem;
          margin-bottom: 1rem;
          border-radius: 0.25rem;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>Delete Poster</h1>
        
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash-messages">
              {% for message in messages %}
                {{ message }}
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        
        <div class="card">
          <p class="warning">Warning: This action cannot be undone!</p>
          
          <div class="details">
            <p>You are about to delete the following poster:</p>
            <h2>{{ poster_id }}</h2>
            <p>{{ poster_title }}</p>
            <p>This will also remove all scores for this poster.</p>
          </div>
          
          <form method="post">
            <a href="{{ url_for('admin_manage_judges_posters') }}?key=adminsecret" class="btn btn-secondary">Cancel</a>
            <button type="submit" class="btn btn-danger">Confirm Delete</button>
          </form>
        </div>
      </div>
    </body>
    </html>
    ''', poster_id=poster_id, poster_title=poster_title)
    
# ===============================
# Run the Application
# ===============================
if __name__ == '__main__':
    app.run(debug=True)
