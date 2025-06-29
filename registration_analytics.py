import sqlite3
import logging
import os
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RegistrationAnalytics:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize_db()

    def initialize_db(self):
        """Initialize analytics tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create registration analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registration_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_data TEXT,
                status TEXT,
                duration_seconds INTEGER
            )
        ''')
        
        # Create registration attempts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registration_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                attempt_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                step TEXT,
                error_type TEXT,
                error_message TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def log_event(self, user_id: int, event_type: str, event_data: Dict[str, Any], status: str = 'success'):
        """Log a registration event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO registration_analytics (user_id, event_type, event_data, status)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                event_type,
                str(event_data),
                status
            ))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error logging event: {str(e)}")
        finally:
            conn.close()

    def log_attempt(self, user_id: int, step: str, error_type: str, error_message: str):
        """Log a registration attempt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO registration_attempts (user_id, step, error_type, error_message)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                step,
                error_type,
                error_message
            ))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error logging attempt: {str(e)}")
        finally:
            conn.close()

    def get_registration_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get registration statistics for the last N days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get total registrations
            cursor.execute('''
                SELECT COUNT(*) 
                FROM registration_analytics 
                WHERE event_type = 'registration' 
                AND event_timestamp >= datetime('now', ?)
            ''', (f'-{days} days',))
            total_registrations = cursor.fetchone()[0]
            
            # Get successful registrations
            cursor.execute('''
                SELECT COUNT(*) 
                FROM registration_analytics 
                WHERE event_type = 'registration' 
                AND status = 'success'
                AND event_timestamp >= datetime('now', ?)
            ''', (f'-{days} days',))
            successful_registrations = cursor.fetchone()[0]
            
            # Get failed registrations
            cursor.execute('''
                SELECT COUNT(*) 
                FROM registration_analytics 
                WHERE event_type = 'registration' 
                AND status = 'failed'
                AND event_timestamp >= datetime('now', ?)
            ''', (f'-{days} days',))
            failed_registrations = cursor.fetchone()[0]
            
            # Get most common errors
            cursor.execute('''
                SELECT error_type, COUNT(*) as count 
                FROM registration_attempts 
                WHERE attempt_timestamp >= datetime('now', ?)
                GROUP BY error_type 
                ORDER BY count DESC 
                LIMIT 5
            ''', (f'-{days} days',))
            common_errors = cursor.fetchall()
            
            return {
                'total_registrations': total_registrations,
                'successful_registrations': successful_registrations,
                'failed_registrations': failed_registrations,
                'success_rate': (successful_registrations / total_registrations * 100 if total_registrations > 0 else 0),
                'common_errors': common_errors
            }
        except sqlite3.Error as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {}
        finally:
            conn.close()
