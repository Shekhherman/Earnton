import os
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationSystem:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize_db()
        self.notification_jobs = {}

    def initialize_db(self):
        """Initialize notification tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT,
                sent_at TIMESTAMP,
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create notification preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_preferences (
                user_id INTEGER PRIMARY KEY,
                daily_summary BOOLEAN DEFAULT TRUE,
                new_videos BOOLEAN DEFAULT TRUE,
                referral_updates BOOLEAN DEFAULT TRUE,
                system_updates BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Create scheduled notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                schedule_time TIMESTAMP,
                recurring BOOLEAN DEFAULT FALSE,
                recurring_interval INTEGER,
                last_sent TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

    async def send_notification(self, user_id: int, 
                             notification_type: str, 
                             message: str, 
                             data: Dict[str, Any] = None,
                             context: ContextTypes.DEFAULT_TYPE = None) -> bool:
        """Send a notification to a user."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check preferences
            cursor.execute('''
                SELECT daily_summary, new_videos, referral_updates, system_updates
                FROM notification_preferences
                WHERE user_id = ?
            ''', (user_id,))
            
            preferences = cursor.fetchone()
            if not preferences:
                # Set default preferences
                cursor.execute('''
                    INSERT INTO notification_preferences (user_id)
                    VALUES (?)
                ''', (user_id,))
                preferences = (True, True, True, True)
            
            # Check if user wants this type of notification
            if notification_type == 'daily_summary' and not preferences[0]:
                return False
            if notification_type == 'new_video' and not preferences[1]:
                return False
            if notification_type == 'referral_update' and not preferences[2]:
                return False
            if notification_type == 'system_update' and not preferences[3]:
                return False
            
            # Store notification
            cursor.execute('''
                INSERT INTO notifications (user_id, type, message, data)
                VALUES (?, ?, ?, ?)
            ''', (user_id, notification_type, message, json.dumps(data) if data else None))
            
            conn.commit()
            conn.close()
            
            # Send notification if context provided
            if context:
                keyboard = [
                    [InlineKeyboardButton("Mark as Read", callback_data=f'read_{user_id}')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=reply_markup
                )
            
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False

    def schedule_notification(self, user_id: int, 
                            notification_type: str, 
                            message: str, 
                            schedule_time: datetime,
                            recurring: bool = False,
                            recurring_interval: int = 86400) -> int:
        """Schedule a notification for future delivery."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO scheduled_notifications 
                (user_id, type, message, schedule_time, recurring, recurring_interval)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, notification_type, message, schedule_time, recurring, recurring_interval))
            
            notification_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return notification_id
        except Exception as e:
            logger.error(f"Error scheduling notification: {str(e)}")
            return -1

    async def process_scheduled_notifications(self):
        """Process all scheduled notifications."""
        while True:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get all notifications that should be sent now
                cursor.execute('''
                    SELECT id, user_id, type, message, recurring, recurring_interval
                    FROM scheduled_notifications
                    WHERE schedule_time <= CURRENT_TIMESTAMP
                    AND (last_sent IS NULL OR last_sent < CURRENT_TIMESTAMP - INTERVAL 1 DAY)
                ''')
                
                notifications = cursor.fetchall()
                
                for notification in notifications:
                    notification_id, user_id, notification_type, message, recurring, interval = notification
                    
                    # Send notification
                    await self.send_notification(user_id, notification_type, message)
                    
                    # Update last sent time
                    cursor.execute('''
                        UPDATE scheduled_notifications
                        SET last_sent = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (notification_id,))
                    
                    # If not recurring, delete
                    if not recurring:
                        cursor.execute('DELETE FROM scheduled_notifications WHERE id = ?', (notification_id,))
                    else:
                        # Schedule next occurrence
                        next_time = datetime.now() + timedelta(seconds=interval)
                        cursor.execute('''
                            UPDATE scheduled_notifications
                            SET schedule_time = ?
                            WHERE id = ?
                        ''', (next_time, notification_id))
                
                conn.commit()
                conn.close()
                
                # Wait before checking again
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error processing scheduled notifications: {str(e)}")
                await asyncio.sleep(60)

    def get_unread_notifications(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all unread notifications for a user."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, type, message, data, created_at
                FROM notifications
                WHERE user_id = ? AND read_at IS NULL
                ORDER BY created_at DESC
            ''', (user_id,))
            
            notifications = []
            for row in cursor.fetchall():
                notifications.append({
                    'id': row[0],
                    'type': row[1],
                    'message': row[2],
                    'data': json.loads(row[3]) if row[3] else None,
                    'created_at': row[4]
                })
            
            conn.close()
            return notifications
        except Exception as e:
            logger.error(f"Error getting notifications: {str(e)}")
            return []

    def mark_notification_read(self, notification_id: int) -> bool:
        """Mark a notification as read."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE notifications
                SET read_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (notification_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error marking notification read: {str(e)}")
            return False
