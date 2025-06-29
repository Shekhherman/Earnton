import sqlite3
import os

# Get the directory of the current script
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'botdata.db')

# Connect to SQLite database (or create it)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create tables for users, agreements, videos, and video watches
# Users table with registration status
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE,
    username TEXT,
    password TEXT,
    gpt_username TEXT,
    gpt_password TEXT,
    credits REAL DEFAULT 0,
    ton_wallet TEXT,
    last_daily TEXT,
    referrer INTEGER,
    registered INTEGER DEFAULT 0,
    agreement_version TEXT
)
''')

# Agreements table
cursor.execute('''
CREATE TABLE IF NOT EXISTS agreements (
    id INTEGER PRIMARY KEY,
    text TEXT,
    version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Insert initial agreement
initial_agreement = '''
By using this bot, you agree to the following terms:
1. You will only watch videos for legitimate purposes
2. You will not abuse the system or attempt to manipulate rewards
3. You understand that rewards are subject to availability
4. You agree to the privacy policy regarding your data
5. You understand that rewards may be subject to network fees
6. You are responsible for any taxes on rewards
'''

cursor.execute('INSERT INTO agreements (text, version) VALUES (?, ?)', 
              (initial_agreement, '1.0'))

# Videos table
cursor.execute('''
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_url TEXT,
    points INTEGER,
    added_by INTEGER,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (added_by) REFERENCES users (user_id)
)
''')

# Video watches table
cursor.execute('''
CREATE TABLE IF NOT EXISTS video_watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    video_id INTEGER,
    watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (video_id) REFERENCES videos (id)
)
''')

# Tasks table
cursor.execute('''
CREATE TABLE IF NOT EXISTS tasks (
    user_id INTEGER,
    task_name TEXT,
    status TEXT,
    PRIMARY KEY(user_id, task_name)
)
''')

# Settings table
cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
''')

# Commit changes and close connection
conn.commit()
conn.close()

print("Database setup completed successfully!")
