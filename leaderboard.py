import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

class Leaderboard:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize_db()

    def initialize_db(self):
        """Initialize leaderboard tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create leaderboard entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard_entries (
                user_id INTEGER,
                points INTEGER,
                date TEXT,
                PRIMARY KEY (user_id, date)
            )
        ''')
        
        # Create user achievements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id INTEGER PRIMARY KEY,
                total_points INTEGER DEFAULT 0,
                daily_wins INTEGER DEFAULT 0,
                weekly_wins INTEGER DEFAULT 0,
                monthly_wins INTEGER DEFAULT 0,
                last_win_date TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def get_leaderboard(self, period: str = 'daily', limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get leaderboard for specified period.
        
        Args:
            period: 'daily', 'weekly', or 'monthly'
            limit: Number of entries to return
            
        Returns:
            list: List of leaderboard entries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_filter = ""
        if period == 'daily':
            date_filter = "WHERE date = date('now')"
        elif period == 'weekly':
            date_filter = "WHERE date >= date('now', '-7 days')"
        elif period == 'monthly':
            date_filter = "WHERE date >= date('now', '-30 days')"
        
        cursor.execute(f'''
            SELECT u.id, u.username, SUM(le.points) as total_points
            FROM users u
            JOIN leaderboard_entries le ON u.id = le.user_id
            {date_filter}
            GROUP BY u.id
            ORDER BY total_points DESC
            LIMIT ?
        ''', (limit,))
        
        leaderboard = []
        for i, row in enumerate(cursor.fetchall(), 1):
            leaderboard.append({
                'rank': i,
                'user_id': row[0],
                'username': row[1],
                'points': row[2]
            })
        
        conn.close()
        return leaderboard

    def update_leaderboard(self, user_id: int, points: int) -> None:
        """
        Update user's points in leaderboard.
        
        Args:
            user_id: Telegram user ID
            points: Points to add
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Update daily leaderboard
        cursor.execute('''
            INSERT INTO leaderboard_entries (user_id, points, date)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, date)
            DO UPDATE SET points = leaderboard_entries.points + ?
        ''', (user_id, points, today, points))
        
        # Update user achievements
        cursor.execute('''
            INSERT OR IGNORE INTO user_achievements (user_id)
            VALUES (?)
        ''', (user_id,))
        
        cursor.execute('''
            UPDATE user_achievements
            SET total_points = total_points + ?
            WHERE user_id = ?
        ''', (points, user_id))
        
        conn.commit()
        conn.close()

    def get_user_rank(self, user_id: int, period: str = 'daily') -> Dict[str, Any]:
        """
        Get user's rank in leaderboard.
        
        Args:
            user_id: Telegram user ID
            period: 'daily', 'weekly', or 'monthly'
            
        Returns:
            dict: User's rank information
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_filter = ""
        if period == 'daily':
            date_filter = "WHERE date = date('now')"
        elif period == 'weekly':
            date_filter = "WHERE date >= date('now', '-7 days')"
        elif period == 'monthly':
            date_filter = "WHERE date >= date('now', '-30 days')"
        
        # Get user's points
        cursor.execute(f'''
            SELECT SUM(points) as user_points
            FROM leaderboard_entries
            WHERE user_id = ?
            {date_filter}
        ''', (user_id,))
        user_points = cursor.fetchone()[0] or 0
        
        # Get total users with higher points
        cursor.execute(f'''
            SELECT COUNT(*)
            FROM (
                SELECT user_id, SUM(points) as total_points
                FROM leaderboard_entries
                {date_filter}
                GROUP BY user_id
                HAVING total_points > ?
            )
        ''', (user_points,))
        rank = cursor.fetchone()[0] + 1
        
        # Get total users in leaderboard
        cursor.execute(f'''
            SELECT COUNT(DISTINCT user_id)
            FROM leaderboard_entries
            {date_filter}
        ''')
        total_users = cursor.fetchone()[0]
        
        conn.close()
        return {
            'rank': rank,
            'total_users': total_users,
            'points': user_points,
            'period': period
        }
