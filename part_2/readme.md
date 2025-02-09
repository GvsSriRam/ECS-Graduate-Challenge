# ECS Research Day Judging Portal

A **Flask** web application designed to manage graduate student poster scoring for an ECS Research Day event. This app automates judge assignments, scoring, and final results display. It uses:

- **Flask** for the web framework
- **SQLite** for data storage
- **Flask-Mail** for sending OTPs to judges
- **OpenPyXL** for reading XLSX spreadsheets
- **Qrcode** for generating QR codes

## Features

1. **Judge Authentication** via email + One-Time Password (OTP).
2. **Judge Dashboard** for viewing assigned posters and entering scores.
3. **Admin Dashboard** (protected by a URL key) to handle:
   - **Import Judges** (XLSX file with judge assignments)
   - **Upload Final Results** (XLSX file with poster ranks)
   - **Export Scores** (CSV and XLSX)
   - **View/Edit Scores** (for admin oversight)
   - **Reset Scores**
   - **Generate QR Codes** for every poster
4. **Final Results** page (publicly accessible) showing top posters in a dark-themed “/dashboard” style.

## Directory Structure

```
your_project/
├── app.py
├── requirements.txt
├── README.md
└── app.db (auto-created on first run, unless you create your own)
```

## Installation

1. **Clone or download** this repository to your local machine.
2. Ensure you have **Python 3.7+** installed (3.10+ recommended).
3. Create and activate a **virtual environment** (optional, but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or
   venv\Scripts\activate     # Windows
   ```
4. **Install required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   A typical `requirements.txt` might include:
   ```
   Flask
   flask-mail
   openpyxl
   qrcode
   ```
5. **Check SMTP Credentials** in `app.py` under `MAIL_USERNAME` and `MAIL_PASSWORD`.
   - Update to your own email/app password or your institution’s SMTP settings.

## Configuration

- **Secret Key**: The application secret key is defined at the top of `app.py`.

  ```python
  app.secret_key = 'your-secret-key-here'
  ```

  Replace this with a secure random key for production.

- **Database**: The code uses an SQLite database `app.db`. If it doesn't exist, it is automatically created on first run. The `init_db` function creates tables needed for judges, scores, etc.

- **Flask-Mail**: In `app.py`, look for:

  ```python
  app.config.update(
      MAIL_SERVER='smtp.gmail.com',
      MAIL_PORT=587,
      MAIL_USE_TLS=True,
      MAIL_USERNAME='your_email@gmail.com',
      MAIL_PASSWORD='your-app-password',
      MAIL_DEFAULT_SENDER='your_email@gmail.com'
  )
  ```

  Change these to **valid credentials** for sending OTP emails.

- **Admin Key**: Many admin endpoints (like `/admin/dashboard`) are protected by `?key=adminsecret`. Replace `'adminsecret'` with your own custom token or upgrade to a more secure mechanism (like a login for admins).

## Usage

1. **Run the Flask App**:

   ```bash
   python app.py
   ```

   By default, Flask runs at `http://127.0.0.1:5000/`.
   
   Note: If the url doesn't open, it might be the issue with the previous session cache. Please try in incognito.

2. **Admin Workflow**:

   1. Navigate to `http://127.0.0.1:5000/admin/dashboard?key=adminsecret` (replace `adminsecret` if you customized).
   2. Use the tiles to:
      - **Import Judges** (`/admin/import_judges?key=adminsecret`): Upload an XLSX with judge assignments.
      - **Remove Judges**: Wipes out all judge data.
      - **Export Scores**: Download a CSV of all scores.
      - **View/Edit Scores**: Manually tweak any judge’s submitted scores.
      - **Reset Scores**: Clears all scores and score history.
      - **Generate All QR Codes**: Create a QR code for each poster.
      - **Export Score Matrix**: Generates an XLSX matrix of [Poster x Judge] scores. This will be used as input for part-3.
      - **Upload Results**: Upload a final XLSX with `Poster-ID` and `Rank` columns.

3. **Judge Workflow**:

   1. A judge visits `http://127.0.0.1:5000/login`.
   2. Enters their **email** (must exist in the `judges` table).
      - Note: A judge cannot login until posters have been assigned to them in part-1.
   3. Receives a 6-digit OTP in their email.
   4. Enters the OTP at `/verify`.
   5. Accesses their `/dashboard`, sees assigned posters, and enters scores.



4. **Viewing the Final Results**:
   - After uploading results at `/admin/upload_results?key=adminsecret`, visit `/results` to see a dark-themed page displaying the top three posters and then all others, sorted by rank.

## Data Models

- **`judges` Table**:

  - `email` (TEXT, primary key)
  - `name` (TEXT)
  - `pin` (TEXT)
  - `assigned_posters` (TEXT, JSON list of poster IDs like `["poster1","poster2"]`)
  - `assigned_poster_titles` (TEXT, JSON dict mapping `'poster1' -> "Poster #1 Title"`, etc.)

- **`judge_info` Table**:

  - `judge_id` (INTEGER, PK)
  - `name` (TEXT)
  - `email` (TEXT, unique)

- **`scores` Table**:

  - `id` (INTEGER, PK, autoincrement)
  - `judge_email` (TEXT)
  - `poster_id` (TEXT)
  - `score` (INTEGER)

- **`score_changes` Table**:
  - `id` (INTEGER, PK, autoincrement)
  - `judge_email` (TEXT)
  - `poster_id` (TEXT)
  - `old_score` (INTEGER)
  - `new_score` (INTEGER)
  - `change_time` (TIMESTAMP, default CURRENT_TIMESTAMP)

## Uploading Files

### 1. **Import Judges**

- Expects an XLSX with columns: `Judge`, `Judge FirstName`, `Judge LastName`, `Email`, `poster-1`, `poster-1-title`, ... `poster-6-title`.
- Creates entries in `judges` and `judge_info`.

### 2. **Upload Results**

- Expects an XLSX with columns: `Poster-ID` and `Rank`.
- Populates `ranking_data` in memory for displaying on `/results`.

## Adding or Modifying Poster Titles

- If the final abstract list is not stored in a dedicated `posters` table, the system collects titles from the `assigned_poster_titles` field in the `judges` table. This means the same poster can appear in multiple judges’ JSON.

## Security Considerations

1. **Production-Ready**:

   - Replace the `"adminsecret"` approach with real authentication for admins.
   - Use environment variables for your mail and DB config.
   - Deploy behind HTTPS so OTP transmissions are secure.

2. **Email Deliverability**:

   - Using Gmail SMTP or any other mail server may require app-passwords or OAuth2 tokens.
   - Make sure to handle email sending errors gracefully.

3. **Session Management**:
   - The app uses `session` for judge login state.
   - Always ensure `app.secret_key` is **kept secret**.

## Common Troubleshooting

1. **`NameError: name 'ranking_data' is not defined`**

   - Make sure `ranking_data` is declared **globally** outside functions, and that you do `global ranking_data` in routes that modify it.

2. **`jinja2.exceptions.UndefinedError: 'enumerate' is undefined`**

   - Use `loop.index0` or pass `enumerate` explicitly into the Jinja context. In this code, we rely on Jinja’s `loop.index0`.

3. **Email Sending Failures**

   - Check your SMTP credentials, ensure “less secure apps” or app-password is configured if using Gmail.

4. **File Parsing Errors**
   - Confirm the XLSX file structure matches the expected columns exactly.
