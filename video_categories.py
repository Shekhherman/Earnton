import sqlite3
import os
from typing import List, Dict, Any

class VideoCategories:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.categories = [
            {'id': 1, 'name': 'Education', 'points': 10},
            {'id': 2, 'name': 'Entertainment', 'points': 8},
            {'id': 3, 'name': 'Technology', 'points': 12},
            {'id': 4, 'name': 'Business', 'points': 15},
            {'id': 5, 'name': 'Health', 'points': 10}
        ]
        self.initialize_db()

    def initialize_db(self):
        """Initialize video categories tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create video categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_categories (
                id INTEGER PRIMARY KEY,
                name TEXT,
                points INTEGER
            )
        ''')
        
        # Create user preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER,
                category_id INTEGER,
                preference_level INTEGER,
                PRIMARY KEY (user_id, category_id)
            )
        ''')
        
        # Create video category mapping table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_category_map (
                video_id INTEGER,
                category_id INTEGER,
                PRIMARY KEY (video_id, category_id)
            )
        ''')
        
        # Insert default categories
        cursor.executemany('INSERT OR IGNORE INTO video_categories (id, name, points) VALUES (?, ?, ?)',
                         [(cat['id'], cat['name'], cat['points']) for cat in self.categories])
        
        conn.commit()
        conn.close()

    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all video categories."""
        return self.categories

    def get_category_points(self, category_id: int) -> int:
        """Get points for a specific category."""
        for cat in self.categories:
            if cat['id'] == category_id:
                return cat['points']
        return 0

    def set_user_preference(self, user_id: int, category_id: int, preference_level: int) -> bool:
        """
        Set user's preference for a category.
        
        Args:
            user_id: Telegram user ID
            category_id: Category ID
            preference_level: 1-5 (1 being least preferred, 5 being most preferred)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if preference_level < 1 or preference_level > 5:
            return False
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO user_preferences 
                (user_id, category_id, preference_level) 
                VALUES (?, ?, ?)
            ''', (user_id, category_id, preference_level))
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()

    def get_user_preferences(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get user's category preferences.
        
        Returns:
            list: List of category preferences
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT vc.id, vc.name, vc.points, up.preference_level
            FROM video_categories vc
            LEFT JOIN user_preferences up ON vc.id = up.category_id AND up.user_id = ?
            ORDER BY CASE WHEN up.preference_level IS NULL THEN 0 ELSE up.preference_level END DESC
        ''', (user_id,))
        
        preferences = []
        for row in cursor.fetchall():
            preferences.append({
                'id': row[0],
                'name': row[1],
                'points': row[2],
                'preference_level': row[3] or 3  # Default to 3 if not set
            })
        
        conn.close()
        return preferences

    def get_recommended_videos(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recommended videos based on user preferences.
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of videos to return
            
        Returns:
            list: List of recommended videos
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user preferences
        preferences = self.get_user_preferences(user_id)
        
        # Get videos ordered by preference
        cursor.execute('''
            SELECT v.id, v.title, v.url, vc.name as category_name, vc.points
            FROM videos v
            JOIN video_category_map vcm ON v.id = vcm.video_id
            JOIN video_categories vc ON vcm.category_id = vc.id
            WHERE vcm.category_id IN (
                SELECT category_id FROM user_preferences WHERE user_id = ?
            )
            ORDER BY (
                SELECT preference_level FROM user_preferences 
                WHERE user_id = ? AND category_id = vcm.category_id
            ) DESC,
            vc.points DESC
            LIMIT ?
        ''', (user_id, user_id, limit))
        
        videos = []
        for row in cursor.fetchall():
            videos.append({
                'id': row[0],
                'title': row[1],
                'url': row[2],
                'category': row[3],
                'points': row[4]
            })
        
        conn.close()
        return videos
