# import sqlite3
# import json

# DATABASE = 'app.db'

# def add_sample_data():
#     conn = sqlite3.connect(DATABASE)
#     cursor = conn.cursor()

#     # Add sample judges
#     sample_judges = [
#         ("preetamkamal@gmail.com", "Judge One", json.dumps(["poster1", "poster2", "poster3"])),
#         ("judge2@example.com", "Judge Two", json.dumps(["poster2", "poster4"]))
#     ]
#     cursor.executemany(
#         "INSERT OR IGNORE INTO judges (email, name, assigned_posters) VALUES (?, ?, ?)",
#         sample_judges
#     )
#     conn.commit()

#     # Add sample scores
#     sample_scores = [
#         ("judge1@example.com", "poster1", 8),
#         ("judge1@example.com", "poster2", 7),
#         ("judge2@example.com", "poster2", 9),
#         ("judge2@example.com", "poster4", 6)
#     ]
#     cursor.executemany(
#         "INSERT OR IGNORE INTO scores (judge_email, poster_id, score) VALUES (?, ?, ?)",
#         sample_scores
#     )
#     conn.commit()

#     conn.close()
#     print("Sample data added.")

# if __name__ == '__main__':
#     add_sample_data()


import sqlite3

DATABASE = 'app.db'

def add_score_changes_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS score_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judge_email TEXT,
            poster_id TEXT,
            old_score INTEGER,
            new_score INTEGER,
            change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("score_changes table created.")

if __name__ == '__main__':
    add_score_changes_table()
