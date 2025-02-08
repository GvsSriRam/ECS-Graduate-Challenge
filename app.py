import os
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# FastAPI application setup
app = FastAPI()

# Path to the Excel file where scores will be stored
EXCEL_FILE = "scores.xlsx"  # Path to your Excel file where scores are saved

# Function to load scores from the Excel file
def load_scores():
    try:
        df = pd.read_excel(EXCEL_FILE)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["judge_id", "poster_id", "score"])

# Function to save scores back to the Excel file
def save_scores(df, file_path=EXCEL_FILE):
    df.to_excel(file_path, index=False)

# Pydantic model for score submission
class ScoreInput(BaseModel):
    judge_id: int
    poster_id: int
    score: int

@app.get("/score/{poster_id}/{judge_id}", response_class=HTMLResponse)
def score_page(poster_id: int,judge_id: int):
    # Get judge's previous score (if any)
    df = load_scores()
    # judge_id = 1  # Assuming the judge ID is 1 for simplicity

    # Check if the judge has already rated this poster
    existing_score = df[(df["judge_id"] == judge_id) & (df["poster_id"] == poster_id)]["score"]

    if not existing_score.empty:
        existing_score = existing_score.iloc[0]  # Get the existing score
    else:
        existing_score = None  # No score submitted yet

    # Create the rating buttons
    score_buttons = "".join([f'<button class="score-btn btn-{i}" onclick="submitScore({i})">{i}</button>' for i in range(1, 11)])

    # Render the page with the current score or "no score" message
    return f"""
    <html>
    <head>
        <title>Rate Poster {poster_id}</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/js/all.min.js"></script>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <style>
            body {{
                background-color: #1e1e2e;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                max-width: 700px;
                padding: 30px;
                background: #282a36;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(255, 255, 255, 0.2);
                text-align: center;
            }}
            .score-btn {{
                font-size: 32px;
                font-weight: bold;
                width: 90px;
                height: 90px;
                margin: 12px;
                border-radius: 50%;
                border: none;
                color: white;
                transition: transform 0.2s ease-in-out, background-color 0.3s;
            }}
            .score-btn:hover {{
                transform: scale(1.2);
            }}
            .btn-1 {{ background-color: #ff595e; }}
            .btn-2 {{ background-color: #ff924c; }}
            .btn-3 {{ background-color: #ffca3a; }}
            .btn-4 {{ background-color: #8ac926; }}
            .btn-5 {{ background-color: #1982c4; }}
            .btn-6 {{ background-color: #6a4c93; }}
            .btn-7 {{ background-color: #ff9f1c; }}
            .btn-8 {{ background-color: #8338ec; }}
            .btn-9 {{ background-color: #3a86ff; }}
            .btn-10 {{ background-color: #ff006e; }}
            
            .success-alert {{
                display: none;
                margin-top: 20px;
                font-size: 20px;
                font-weight: bold;
                color: #28a745;
                animation: fadeIn 0.5s;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; }}
                to {{ opacity: 1; }}
            }}
            h1 {{
                font-size: 36px;
                margin-bottom: 20px;
                font-weight: bold;
            }}
            p {{
                font-size: 20px;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1><i class="fas fa-star"></i> Rate Poster {poster_id}</h1>
            <p>Tap a number to submit your rating:</p>

            {f'<p>Previous Rating: {existing_score}</p>' if existing_score else "<p>No score submitted yet.</p>"}

            <div>
                {score_buttons}
            </div>
            <div id="success-message" class="alert success-alert">
                ✅ Your score has been submitted!
            </div>
        </div>

        <script>
            function submitScore(score) {{
                fetch("/submit_score/", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ "judge_id": {judge_id}, "poster_id": {poster_id}, "score": score }})
                }}).then(response => response.json())
                  .then(data => {{
                      document.getElementById("success-message").style.display = "block";
                      setTimeout(() => {{
                          document.getElementById("success-message").style.display = "none";
                          location.reload();  // Reload the page to reflect the updated score
                      }}, 2000);
                  }})
                  .catch(error => console.error("Error:", error));
            }}
        </script>
    </body>
    </html>
    """

@app.post("/submit_score/")
def submit_score(score_input: ScoreInput):
    # Load the current scores from scores.xlsx
    df_scores = load_scores()

    # Check if the judge has already rated this poster
    existing_score_index = df_scores[(df_scores["judge_id"] == score_input.judge_id) & (df_scores["poster_id"] == score_input.poster_id)].index

    if not existing_score_index.empty:
        # Update the existing score
        df_scores.loc[existing_score_index, "score"] = score_input.score
    else:
        # Insert a new record if it doesn't exist
        new_score = pd.DataFrame([{
            "judge_id": score_input.judge_id,
            "poster_id": score_input.poster_id,
            "score": score_input.score
        }])
        df_scores = pd.concat([df_scores, new_score], ignore_index=True)

    # Save the updated dataframe back to scores.xlsx
    save_scores(df_scores)

    # Load Poster_Judge_Scores.xlsx
    file_path_poster_judge = "Poster_Judge_Scores.xlsx"
    try:
        df_poster_judge = pd.read_excel(file_path_poster_judge, index_col=0)
    except FileNotFoundError:
        return {"error": "Poster_Judge_Scores.xlsx not found!"}

    # Convert judge_id to match column name format (assuming it’s "Judge X")
    judge_column = f"Judge {score_input.judge_id}"

    # Check if judge column exists
    if judge_column not in df_poster_judge.columns:
        return {"error": f"Judge ID {score_input.judge_id} does not exist in Poster_Judge_Scores.xlsx!"}

    # Check if poster row exists
    poster_row = f"Poster {score_input.poster_id}"
    if poster_row not in df_poster_judge.index:
        return {"error": f"Poster ID {score_input.poster_id} does not exist in Poster_Judge_Scores.xlsx!"}

    # Update the score in the Poster_Judge_Scores.xlsx file
    df_poster_judge.at[poster_row, judge_column] = score_input.score

    # Save the updated dataframe back to Poster_Judge_Scores.xlsx
    df_poster_judge.to_excel(file_path_poster_judge)

    return {"message": "Score submitted successfully"}

@app.get("/scores_table", response_class=HTMLResponse)
def scores_table():
    # Load scores from the Excel file
    df = load_scores()

    return f"""
    <html>
    <head><title>Scores Table</title></head>
    <body>
        <h2>Scores Table:</h2>
        <pre>{df.to_html(index=False)}</pre>
    </body>
    </html>
    """