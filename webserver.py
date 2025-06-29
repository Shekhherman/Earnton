from flask import Flask, request, render_template_string, send_from_directory, redirect
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# --- Database setup ---
conn = sqlite3.connect('botdata.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    credits REAL DEFAULT 0,
    ton_wallet TEXT,
    last_daily TEXT,
    referrer INTEGER
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS tasks (
    user_id INTEGER,
    task_name TEXT,
    status TEXT,
    PRIMARY KEY(user_id, task_name)
)
''')
conn.commit()

def add_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
        conn.commit()

@app.route('/redirect/<user_id>')
def redirect_video(user_id):
    add_user(int(user_id))
    cursor.execute('INSERT OR REPLACE INTO tasks (user_id, task_name, status) VALUES (?, ?, ?)', 
                  (int(user_id), 'watch', 'started'))
    conn.commit()
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Watch Video</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 20px; }
        video { width: 100%; max-width: 800px; margin: 20px auto; }
        #status { margin-top: 20px; }
    </style>
</head>
<body>
    <h2>Watch this video to earn credits</h2>
    <video id="video" controls>
        <source src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4" type="video/mp4">
        Your browser does not support the video tag.
    </video>
    <div id="status"></div>
    <script>
        const video = document.getElementById('video');
        const statusDiv = document.getElementById('status');
        
        video.onplay = function() {
            statusDiv.textContent = 'Video is playing...';
        };
        
        video.onended = function() {
            statusDiv.textContent = 'Video completed! Updating credits...';
            fetch(`/watched?user_id=${user_id}`)
                .then(response => response.json())
                .then(data => {
                    statusDiv.textContent = data.message;
                })
                .catch(err => {
                    statusDiv.textContent = 'Error: ' + err;
                });
        };
    </script>
</body>
</html>
''')

@app.route('/watched')
def watched():
    user_id = request.args.get('user_id')
    if not user_id:
        return {'error': 'User ID required'}, 400
    
    try:
        user_id = int(user_id)
        add_user(user_id)
        
        # Update task status
        cursor.execute('UPDATE tasks SET status = ? WHERE user_id = ? AND task_name = ?', 
                      ('completed', user_id, 'watch'))
        
        # Update credits
        cursor.execute('SELECT credits FROM users WHERE user_id = ?', (user_id,))
        current_credits = cursor.fetchone()[0]
        new_credits = current_credits + 0.1  # 0.1 credits per video
        cursor.execute('UPDATE users SET credits = ? WHERE user_id = ?', (new_credits, user_id))
        
        conn.commit()
        return {'message': 'Credits updated successfully!', 'new_credits': new_credits}
    except Exception as e:
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(port=8888)

# --- HTML Page for video ---
video_page = '''
<!DOCTYPE html>
<html>
<head><title>Watch Video</title></head>
<body>
<h2>Watch this video to earn credits</h2>
<video id="video" width="640" controls>
  <source src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>
<script>
const video = document.getElementById('video');
video.onended = function() {
    fetch('/watched?user_id={{ user_id }}')
        .then(response => {
            if(response.ok) alert('You earned credits!');
            else alert('Failed to update credits.');
        })
        .catch(err => alert('Error sending watch confirmation.'));
};
</script>
</body>
</html>
'''

# --- Route to serve video page ---
@app.route('/video/<user_id>')
def video(user_id):
    add_user(user_id)
    return render_template_string(video_page, user_id=user_id)

# --- Route called after video watched ---
@app.route('/watched')
def watched():
    user_id = request.args.get('user_id')
    if user_id:
        add_user(user_id)
        cursor.execute('UPDATE users SET balance = balance + 10 WHERE user_id = ?', (user_id,))
        conn.commit()
        print(f"User {user_id} earned 10 credits!")
        return "Credits added", 200
    return "User ID missing", 400

# --- Redirect page to bypass localtunnel password ---
@app.route('/redirect/<user_id>')
def redirect_page(user_id):
    return send_from_directory(os.getcwd(), 'redirect.html')

if __name__ == '__main__':
    app.run(port=5000)
