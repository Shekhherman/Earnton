import re
import sqlite3
from typing import Dict, Any
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityChecks:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize_db()

    def initialize_db(self):
        """Initialize security tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create security rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_type TEXT NOT NULL,
                rule_value TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create failed attempts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failed_attempts (
                user_id INTEGER,
                attempt_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def validate_username(self, username: str) -> Dict[str, Any]:
        """Validate username format and uniqueness."""
        if not username:
            return {'valid': False, 'error': 'Username cannot be empty'}
            
        if len(username) < 3:
            return {'valid': False, 'error': 'Username must be at least 3 characters'}
            
        if not username.isalnum():
            return {'valid': False, 'error': 'Username must contain only letters and numbers'}
            
        if not re.match(r'^[a-zA-Z0-9]+$', username):
            return {'valid': False, 'error': 'Username contains invalid characters'}
            
        # Check if username exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return {'valid': False, 'error': 'Username already exists'}
            
        conn.close()
        return {'valid': True}

    def validate_password(self, password: str) -> Dict[str, Any]:
        """Validate password strength."""
        if not password:
            return {'valid': False, 'error': 'Password cannot be empty'}
            
        if len(password) < 8:
            return {'valid': False, 'error': 'Password must be at least 8 characters'}
            
        # Check password complexity
        if not any(char.isdigit() for char in password):
            return {'valid': False, 'error': 'Password must contain at least one number'}
            
        if not any(char.isalpha() for char in password):
            return {'valid': False, 'error': 'Password must contain at least one letter'}
            
        if not any(char.isupper() for char in password):
            return {'valid': False, 'error': 'Password must contain at least one uppercase letter'}
            
        if not any(char.islower() for char in password):
            return {'valid': False, 'error': 'Password must contain at least one lowercase letter'}
            
        # Check common patterns
        common_patterns = ['123', 'password', 'qwerty', 'admin']
        if any(pattern in password.lower() for pattern in common_patterns):
            return {'valid': False, 'error': 'Password contains common patterns'}
            
        return {'valid': True}

    def validate_gpt_credentials(self, username: str, password: str) -> Dict[str, Any]:
        """Validate GPT platform credentials format."""
        if not username or not password:
            return {'valid': False, 'error': 'Credentials cannot be empty'}
            
        if len(username) < 3:
            return {'valid': False, 'error': 'Username must be at least 3 characters'}
            
        if len(password) < 6:
            return {'valid': False, 'error': 'Password must be at least 6 characters'}
            
        # Check for common patterns
        if username.lower() in ['admin', 'root', 'test']:
            return {'valid': False, 'error': 'Invalid username'}
            
        if password.lower() in ['password', '123456', 'qwerty']:
            return {'valid': False, 'error': 'Invalid password'}
            
        return {'valid': True}

    def log_failed_attempt(self, user_id: int, attempt_type: str, reason: str):
        """Log failed attempt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO failed_attempts (user_id, attempt_type, reason)
                VALUES (?, ?, ?)
            ''', (user_id, attempt_type, reason))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error logging failed attempt: {str(e)}")
        finally:
            conn.close()

    def check_rate_limit(self, user_id: int, attempt_type: str, limit: int = 5, period: int = 3600) -> bool:
        """Check if user has exceeded rate limit for specific action."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT COUNT(*) 
                FROM failed_attempts 
                WHERE user_id = ? 
                AND attempt_type = ? 
                AND timestamp >= datetime('now', ?)
            ''', (user_id, attempt_type, f'-{period} seconds'))
            
            count = cursor.fetchone()[0]
            return count < limit
            
        except sqlite3.Error as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return True
        finally:
            conn.close()

    def get_security_rules(self) -> Dict[str, Any]:
        """Get all security rules."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT rule_type, rule_value, description FROM security_rules')
            rules = cursor.fetchall()
            return {
                rule[0]: {
                    'value': rule[1],
                    'description': rule[2]
                } for rule in rules
            }
        except sqlite3.Error as e:
            logger.error(f"Error getting security rules: {str(e)}")
            return {}
        finally:
            conn.close()
