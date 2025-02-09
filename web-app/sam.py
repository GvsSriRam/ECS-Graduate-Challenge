import sqlite3

DATABASE = 'app.db'

def check_data():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # optional: for named columns
    cursor = conn.cursor()

    # Example: Print all rows from the judges table
    cursor.execute("SELECT * FROM judges")
    rows = cursor.fetchall()
    print("Judges Table:")
    for row in rows:
        print(dict(row))
    
    # Example: Print all rows from the scores table
    cursor.execute("SELECT * FROM scores")
    rows = cursor.fetchall()
    print("\nScores Table:")
    for row in rows:
        print(dict(row))
    
    conn.close()

if __name__ == "__main__":
    check_data()
