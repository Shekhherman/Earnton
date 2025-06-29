import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Analytics:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize_db()

    def initialize_db(self):
        """Initialize analytics tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create user activity table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                command TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT TRUE,
                duration REAL
            )
        ''')
        
        # Create video analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER,
                views INTEGER DEFAULT 0,
                unique_views INTEGER DEFAULT 0,
                avg_watch_time REAL DEFAULT 0,
                last_view TIMESTAMP
            )
        ''')
        
        # Create user engagement table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_engagement (
                user_id INTEGER PRIMARY KEY,
                total_commands INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                last_active TIMESTAMP,
                engagement_score REAL DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()

    def log_command(self, user_id: int, command: str, success: bool = True, duration: float = 0.0) -> None:
        """Log command execution."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO user_activity (user_id, command, success, duration)
                VALUES (?, ?, ?, ?)
            ''', (user_id, command, success, duration))
            
            # Update user engagement
            cursor.execute('''
                INSERT OR REPLACE INTO user_engagement 
                (user_id, total_commands, last_active)
                VALUES 
                (?, 
                 COALESCE((SELECT total_commands FROM user_engagement WHERE user_id = ?), 0) + 1,
                 CURRENT_TIMESTAMP)
            ''', (user_id, user_id))
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error logging command: {str(e)}")
        finally:
            conn.close()

    def log_video_view(self, video_id: int, user_id: int, watch_time: float) -> None:
        """Log video view statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Update video analytics
            cursor.execute('''
                INSERT OR REPLACE INTO video_analytics 
                (id, video_id, views, unique_views, avg_watch_time, last_view)
                VALUES 
                (?, 
                 ?,
                 COALESCE((SELECT views FROM video_analytics WHERE video_id = ?), 0) + 1,
                 COALESCE((SELECT CASE 
                     WHEN EXISTS (SELECT 1 FROM video_analytics WHERE video_id = ? AND user_id = ?) 
                     THEN unique_views 
                     ELSE unique_views + 1 
                     END FROM video_analytics WHERE video_id = ?), 1),
                 (SELECT CASE 
                     WHEN EXISTS (SELECT 1 FROM video_analytics WHERE video_id = ?) 
                     THEN (avg_watch_time * views + ?) / (views + 1) 
                     ELSE ? 
                     END FROM video_analytics WHERE video_id = ?),
                 CURRENT_TIMESTAMP)
            ''', (video_id, video_id, video_id, video_id, user_id, 
                  video_id, video_id, watch_time, watch_time, video_id))
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error logging video view: {str(e)}")
        finally:
            conn.close()

    def get_user_engagement(self, user_id: int) -> Dict[str, Any]:
        """Get user engagement statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT total_commands, avg_response_time, 
                       last_active, engagement_score 
                FROM user_engagement 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'total_commands': result[0],
                    'avg_response_time': result[1],
                    'last_active': result[2],
                    'engagement_score': result[3]
                }
            return {
                'total_commands': 0,
                'avg_response_time': 0.0,
                'last_active': None,
                'engagement_score': 0.0
            }
        except sqlite3.Error as e:
            logger.error(f"Error getting engagement: {str(e)}")
            return {
                'total_commands': 0,
                'avg_response_time': 0.0,
                'last_active': None,
                'engagement_score': 0.0
            }
        finally:
            conn.close()

    def get_video_analytics(self, video_id: int) -> Dict[str, Any]:
        """Get video analytics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT views, unique_views, avg_watch_time, last_view 
                FROM video_analytics 
                WHERE video_id = ?
            ''', (video_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'views': result[0],
                    'unique_views': result[1],
                    'avg_watch_time': result[2],
                    'last_view': result[3]
                }
            return {
                'views': 0,
                'unique_views': 0,
                'avg_watch_time': 0.0,
                'last_view': None
            }
        except sqlite3.Error as e:
            logger.error(f"Error getting video analytics: {str(e)}")
            return {
                'views': 0,
                'unique_views': 0,
                'avg_watch_time': 0.0,
                'last_view': None
            }
        finally:
            conn.close()

    def get_daily_stats(self) -> Dict[str, Any]:
        """Get daily statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get active users
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id)
                FROM user_activity
                WHERE timestamp >= date('now', '-1 days')
            ''')
            active_users = cursor.fetchone()[0]
            
            # Get total commands
            cursor.execute('''
                SELECT COUNT(*)
                FROM user_activity
                WHERE timestamp >= date('now', '-1 days')
            ''')
            total_commands = cursor.fetchone()[0]
            
            # Get video views
            cursor.execute('''
                SELECT SUM(views)
                FROM video_analytics
                WHERE last_view >= date('now', '-1 days')
            ''')
            video_views = cursor.fetchone()[0] or 0
            
            # Get new users
            cursor.execute('''
                SELECT COUNT(*)
                FROM users
                WHERE registration_date >= date('now', '-1 days')
            ''')
            new_users = cursor.fetchone()[0]
            
            return {
                'active_users': active_users,
                'total_commands': total_commands,
                'video_views': video_views,
                'new_users': new_users
            }
        except sqlite3.Error as e:
            logger.error(f"Error getting daily stats: {str(e)}")
            return {
                'active_users': 0,
                'total_commands': 0,
                'video_views': 0,
                'new_users': 0
            }
        finally:
            conn.close()
