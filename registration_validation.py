import re
import string
import time
from typing import Dict, Any, Optional
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RegistrationValidator:
    def __init__(self):
        self.username_pattern = re.compile(r'^[a-zA-Z0-9_]{3,20}$')
        self.password_pattern = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$')
        self.common_passwords = self._load_common_passwords()
        
    def _load_common_passwords(self) -> set:
        """Load common passwords from file."""
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'common_passwords.txt'), 'r') as f:
                return set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            logger.warning("Common passwords file not found")
            return set()

    def validate_username(self, username: str) -> Dict[str, Any]:
        """Validate username format and uniqueness."""
        if not username:
            return {'valid': False, 'error': 'Username cannot be empty'}
            
        if not self.username_pattern.match(username):
            return {'valid': False, 'error': 'Username must be 3-20 characters and contain only letters, numbers, and underscores'}
            
        if username.lower() in ['admin', 'root', 'test', 'user']:
            return {'valid': False, 'error': 'This username is reserved'}
            
        return {'valid': True}

    def validate_password(self, password: str) -> Dict[str, Any]:
        """Validate password strength and format."""
        if not password:
            return {'valid': False, 'error': 'Password cannot be empty'}
            
        if len(password) < 8:
            return {'valid': False, 'error': 'Password must be at least 8 characters'}
            
        if not self.password_pattern.match(password):
            return {'valid': False, 'error': 'Password must contain at least one uppercase letter, one lowercase letter, and one number'}
            
        if any(char in string.punctuation for char in password):
            return {'valid': False, 'error': 'Password cannot contain special characters'}
            
        if password.lower() in self.common_passwords:
            return {'valid': False, 'error': 'Password is too common'}
            
        return {'valid': True}

    def validate_gpt_credentials(self, username: str, password: str) -> Dict[str, Any]:
        """Validate GPT platform credentials."""
        if not username or not password:
            return {'valid': False, 'error': 'Credentials cannot be empty'}
            
        if not username.isalnum():
            return {'valid': False, 'error': 'GPT username must contain only letters and numbers'}
            
        if len(username) < 3 or len(username) > 20:
            return {'valid': False, 'error': 'GPT username must be 3-20 characters'}
            
        if len(password) < 6:
            return {'valid': False, 'error': 'GPT password must be at least 6 characters'}
            
        if username.lower() in ['admin', 'root', 'test', 'user']:
            return {'valid': False, 'error': 'This username is reserved'}
            
        return {'valid': True}

    def validate_registration(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete registration data."""
        errors = {}
        
        # Validate username
        username_result = self.validate_username(user_data.get('username', ''))
        if not username_result['valid']:
            errors['username'] = username_result['error']
            
        # Validate password
        password_result = self.validate_password(user_data.get('password', ''))
        if not password_result['valid']:
            errors['password'] = password_result['error']
            
        # Validate GPT credentials
        gpt_username = user_data.get('gpt_username', '')
        gpt_password = user_data.get('gpt_password', '')
        if gpt_username and gpt_password:
            gpt_result = self.validate_gpt_credentials(gpt_username, gpt_password)
            if not gpt_result['valid']:
                errors['gpt_credentials'] = gpt_result['error']
                
        return {
            'valid': not bool(errors),
            'errors': errors
        }

    def get_validation_report(self, user_data: Dict[str, Any]) -> str:
        """Generate a validation report for debugging."""
        report = []
        
        # Username validation
        username_result = self.validate_username(user_data.get('username', ''))
        report.append(f"Username: {'✓' if username_result['valid'] else '✗'}")
        if not username_result['valid']:
            report.append(f"  - {username_result['error']}")
            
        # Password validation
        password_result = self.validate_password(user_data.get('password', ''))
        report.append(f"Password: {'✓' if password_result['valid'] else '✗'}")
        if not password_result['valid']:
            report.append(f"  - {password_result['error']}")
            
        # GPT credentials
        gpt_username = user_data.get('gpt_username', '')
        gpt_password = user_data.get('gpt_password', '')
        if gpt_username and gpt_password:
            gpt_result = self.validate_gpt_credentials(gpt_username, gpt_password)
            report.append(f"GPT Credentials: {'✓' if gpt_result['valid'] else '✗'}")
            if not gpt_result['valid']:
                report.append(f"  - {gpt_result['error']}")
                
        return "\n".join(report)

    def validate_rate_limit(self, user_id: int, db_path: str) -> bool:
        """Check if user has exceeded rate limit."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT COUNT(*) 
                FROM registration_attempts 
                WHERE user_id = ? 
                AND attempt_timestamp >= datetime('now', '-1 hour')
            ''', (user_id,))
            
            attempts = cursor.fetchone()[0]
            return attempts < 5
            
        except sqlite3.Error as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return True
            
        finally:
            conn.close()

    def log_validation_attempt(self, user_id: int, step: str, result: Dict[str, Any], db_path: str):
        """Log validation attempt to database."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO registration_attempts 
                (user_id, step, validation_result, attempt_timestamp)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                user_id,
                step,
                str(result),
            ))
            conn.commit()
            
        except sqlite3.Error as e:
            logger.error(f"Error logging validation attempt: {str(e)}")
            
        finally:
            conn.close()
