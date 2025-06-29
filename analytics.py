import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio
from dataclasses import dataclass
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CommandMetrics:
    total: int = 0
    success: int = 0
    failure: int = 0
    avg_duration: float = 0.0
    last_executed: datetime = datetime.min

class Analytics:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize_db()
        self.command_metrics: Dict[str, CommandMetrics] = defaultdict(CommandMetrics)
        self._cleanup_task: Optional[asyncio.Task] = None

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
                duration REAL,
                response_time REAL
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
                total_watch_time REAL DEFAULT 0,
                last_view TIMESTAMP,
                rating REAL DEFAULT 0,
                ratings_count INTEGER DEFAULT 0
            )
        ''')
        
        # Create user engagement table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_engagement (
                user_id INTEGER PRIMARY KEY,
                total_commands INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                total_response_time REAL DEFAULT 0,
                last_active TIMESTAMP,
                engagement_score REAL DEFAULT 0,
                points INTEGER DEFAULT 0,
                balance REAL DEFAULT 0
            )
        ''')
        
        # Create referral analytics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_analytics (
                referrer_id INTEGER,
                referred_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bonus_points INTEGER,
                level INTEGER,
                PRIMARY KEY (referrer_id, referred_id)
            )
        ''')
        
        conn.commit()
        conn.close()

    async def log_command(self, 
                         user_id: int, 
                         command: str, 
                         success: bool = True, 
                         duration: float = 0.0,
                         response_time: float = 0.0) -> None:
        """Log command execution."""
        try:
            # Update in-memory metrics
            metrics = self.command_metrics[command]
            metrics.total += 1
            if success:
                metrics.success += 1
            else:
                metrics.failure += 1
            metrics.avg_duration = (metrics.avg_duration + duration) / metrics.total
            metrics.last_executed = datetime.now()
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO user_activity 
                    (user_id, command, success, duration, response_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, command, success, duration, response_time))
                
                # Update user engagement
                cursor.execute('''
                    INSERT OR REPLACE INTO user_engagement 
                    (user_id, total_commands, total_response_time, last_active)
                    VALUES 
                    (?, 
                     COALESCE((SELECT total_commands FROM user_engagement WHERE user_id = ?), 0) + 1,
                     COALESCE((SELECT total_response_time FROM user_engagement WHERE user_id = ?), 0) + ?,
                     CURRENT_TIMESTAMP)
                ''', (user_id, user_id, user_id, response_time))
                
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Error logging command: {str(e)}")
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error in log_command: {str(e)}")

    async def log_video_view(self, 
                            video_id: int, 
                            user_id: int, 
                            watch_time: float,
                            rating: Optional[float] = None) -> None:
        """Log video view statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Update video analytics
                cursor.execute('''
                    INSERT OR REPLACE INTO video_analytics 
                    (id, video_id, views, unique_views, total_watch_time, avg_watch_time, last_view)
                    VALUES 
                    (?, 
                     ?,
                     COALESCE((SELECT views FROM video_analytics WHERE video_id = ?), 0) + 1,
                     COALESCE((SELECT unique_views FROM video_analytics WHERE video_id = ?), 0) + 1,
                     COALESCE((SELECT total_watch_time FROM video_analytics WHERE video_id = ?), 0) + ?,
                     COALESCE((SELECT total_watch_time FROM video_analytics WHERE video_id = ?), 0) + ? /
                     (COALESCE((SELECT views FROM video_analytics WHERE video_id = ?), 0) + 1),
                     CURRENT_TIMESTAMP)
                ''', (video_id, video_id, video_id, video_id, video_id, watch_time,
                      video_id, watch_time, video_id))
                
                # Update rating if provided
                if rating is not None:
                    cursor.execute('''
                        INSERT OR REPLACE INTO video_analytics 
                        (id, video_id, rating, ratings_count)
                        VALUES 
                        (?,
                         ?,
                         COALESCE((SELECT rating FROM video_analytics WHERE video_id = ?), 0) + ?,
                         COALESCE((SELECT ratings_count FROM video_analytics WHERE video_id = ?), 0) + 1)
                    ''', (video_id, video_id, video_id, rating, video_id))
                
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Error logging video view: {str(e)}")
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error in log_video_view: {str(e)}")

    async def get_command_metrics(self, command: str) -> CommandMetrics:
        """Get metrics for a specific command."""
        return self.command_metrics.get(command, CommandMetrics())

    async def get_user_engagement(self, user_id: int) -> Dict[str, Any]:
        """Get engagement metrics for a user."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT total_commands, avg_response_time, points, balance
                FROM user_engagement
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'total_commands': result[0],
                    'avg_response_time': result[1],
                    'points': result[2],
                    'balance': result[3]
                }
            return {
                'total_commands': 0,
                'avg_response_time': 0.0,
                'points': 0,
                'balance': 0.0
            }
        except Exception as e:
            logger.error(f"Error getting user engagement: {str(e)}")
            return {
                'total_commands': 0,
                'avg_response_time': 0.0,
                'points': 0,
                'balance': 0.0
            }

    async def get_video_statistics(self, video_id: int) -> Dict[str, Any]:
        """Get statistics for a video."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT views, unique_views, avg_watch_time, rating
                FROM video_analytics
                WHERE video_id = ?
            ''', (video_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'views': result[0],
                    'unique_views': result[1],
                    'avg_watch_time': result[2],
                    'rating': result[3]
                }
            return {
                'views': 0,
                'unique_views': 0,
                'avg_watch_time': 0.0,
                'rating': 0.0
            }
        except Exception as e:
            logger.error(f"Error getting video statistics: {str(e)}")
            return {
                'views': 0,
                'unique_views': 0,
                'avg_watch_time': 0.0,
                'rating': 0.0
            }

    async def get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by engagement."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, total_commands, points, balance
                FROM user_engagement
                ORDER BY engagement_score DESC
                LIMIT ?
            ''', (limit,))
            
            return [{
                'user_id': row[0],
                'total_commands': row[1],
                'points': row[2],
                'balance': row[3]
            } for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting top users: {str(e)}")
            return []

    async def get_top_videos(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top videos by views and engagement."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT video_id, views, unique_views, avg_watch_time, rating
                FROM video_analytics
                ORDER BY views DESC, rating DESC
                LIMIT ?
            ''', (limit,))
            
            return [{
                'video_id': row[0],
                'views': row[1],
                'unique_views': row[2],
                'avg_watch_time': row[3],
                'rating': row[4]
            } for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting top videos: {str(e)}")
            return []

    async def cleanup_old_data(self) -> None:
        """Clean up old analytics data."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete old activity data (keep last 30 days)
            cursor.execute('''
                DELETE FROM user_activity
                WHERE timestamp < datetime('now', '-30 days')
            ''')
            
            # Delete old video analytics (keep last 90 days)
            cursor.execute('''
                DELETE FROM video_analytics
                WHERE last_view < datetime('now', '-90 days')
            ''')
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
        finally:
            conn.close()

    def start_cleanup_task(self) -> None:
        """Start background task for periodic data cleanup."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        async def cleanup_loop():
            while True:
                try:
                    await self.cleanup_old_data()
                    await asyncio.sleep(86400)  # Run once per day
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {str(e)}")
                    await asyncio.sleep(60)  # Wait before retrying
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())

# Initialize analytics system
ANALYTICS_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analytics.db')
analytics = Analytics(ANALYTICS_DB_PATH)

# Start cleanup task
analytics.start_cleanup_task()
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
