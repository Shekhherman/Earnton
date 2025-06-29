import os
import logging
from typing import Optional, Dict, Any
import sqlite3
from datetime import datetime, timedelta
import hashlib
import secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize_db()

    def initialize_db(self):
        """Initialize security tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create security logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create rate limits table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rate_limits (
                user_id INTEGER PRIMARY KEY,
                last_request TIMESTAMP,
                request_count INTEGER DEFAULT 0,
                last_reset TIMESTAMP
            )
        ''')
        
        # Create session tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER,
                expires TIMESTAMP,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

    def log_action(self, user_id: int, action: str, details: Optional[str] = None) -> None:
        """Log security-related actions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO security_logs (user_id, action, details)
                VALUES (?, ?, ?)
            ''', (user_id, action, details))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error logging action: {str(e)}")
        finally:
            conn.close()

    def check_rate_limit(self, user_id: int, limit: int = 100, period: int = 3600) -> bool:
        """Check if user has exceeded rate limit."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get current count and reset time
            cursor.execute('''
                SELECT request_count, last_reset 
                FROM rate_limits 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                # Initialize if doesn't exist
                cursor.execute('''
                    INSERT INTO rate_limits (user_id, last_reset) 
                    VALUES (?, CURRENT_TIMESTAMP)
                ''', (user_id,))
                return True
            
            count, last_reset = result
            current_time = datetime.now()
            
            # Check if period has passed
            if (current_time - datetime.strptime(last_reset, '%Y-%m-%d %H:%M:%S')).total_seconds() > period:
                # Reset count
                cursor.execute('''
                    UPDATE rate_limits 
                    SET request_count = 1, 
                        last_reset = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                return True
            
            # Check current count
            if count >= limit:
                return False
                
            # Increment count
            cursor.execute('''
                UPDATE rate_limits 
                SET request_count = request_count + 1 
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Rate limit check error: {str(e)}")
            return True
        finally:
            conn.close()

    def generate_session_token(self, user_id: int, expires_in: int = 86400) -> str:
        """Generate secure session token."""
        token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(seconds=expires_in)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO session_tokens (token, user_id, expires)
                VALUES (?, ?, ?)
            ''', (token, user_id, expires))
            conn.commit()
            return token
        except sqlite3.Error as e:
            logger.error(f"Error generating token: {str(e)}")
            return ""
        finally:
            conn.close()

    def validate_session_token(self, token: str) -> Optional[int]:
        """Validate session token and return user_id if valid."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT user_id 
                FROM session_tokens 
                WHERE token = ? AND expires > CURRENT_TIMESTAMP
            ''', (token,))
            
            result = cursor.fetchone()
            if result:
                return result[0]
            return None
        except sqlite3.Error as e:
            logger.error(f"Token validation error: {str(e)}")
            return None
        finally:
            conn.close()

    def hash_password(self, password: str) -> str:
        """Securely hash password using PBKDF2 with SHA-256."""
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return f"{salt}${key.hex()}"

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hashed value."""
        try:
            salt, key = hashed.split('$')
            calculated_key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return calculated_key.hex() == key
        except:
            return False

    def get_user_ip(self, update: Any) -> Optional[str]:
        """Get user's IP address from update."""
        try:
            if update.message:
                return update.message.effective_chat.id
            elif update.callback_query:
                return update.callback_query.message.effective_chat.id
            return None
        except:
            return None
