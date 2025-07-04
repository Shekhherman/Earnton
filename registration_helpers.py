from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import time
import logging

logger = logging.getLogger(__name__)

class RegistrationHelper:
    def __init__(self):
        self.attempt_limits = {
            'username': 3,
            'password': 3,
            'gpt_credentials': 3,
            'confirmation': 2
        }
        
    def get_time_remaining(self, user_id: int, step: str) -> Optional[timedelta]:
        """Get time remaining until next attempt."""
        conn = sqlite3.connect('botdata.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT attempt_timestamp 
                FROM registration_attempts 
                WHERE user_id = ? AND step = ? 
                ORDER BY attempt_timestamp DESC 
                LIMIT 1
            ''', (user_id, step))
            
            last_attempt = cursor.fetchone()
            if not last_attempt:
                return None
                
            last_time = datetime.strptime(last_attempt[0], '%Y-%m-%d %H:%M:%S')
            cooldown = timedelta(minutes=5)
            
            if datetime.now() - last_time < cooldown:
                return cooldown - (datetime.now() - last_time)
                
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting time remaining: {str(e)}")
            return None
            
        finally:
            conn.close()

    def get_remaining_attempts(self, user_id: int, step: str) -> int:
        """Get remaining attempts for a step."""
        conn = sqlite3.connect('botdata.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT COUNT(*) 
                FROM registration_attempts 
                WHERE user_id = ? AND step = ? 
                AND attempt_timestamp >= datetime('now', '-1 hour')
            ''', (user_id, step))
            
            attempts = cursor.fetchone()[0]
            return max(0, self.attempt_limits.get(step, 3) - attempts)
            
        except sqlite3.Error as e:
            logger.error(f"Error getting remaining attempts: {str(e)}")
            return 0
            
        finally:
            conn.close()

    def format_validation_report(self, validation_result: Dict[str, Any]) -> str:
        """Format validation report for display."""
        report = []
        
        if validation_result.get('username'):
            report.append("Username Requirements:")
            report.append("✓ 3-20 characters")
            report.append("✓ Only letters and numbers")
            report.append("✓ No special characters")
            report.append("✓ No reserved words")
            
        if validation_result.get('password'):
            report.append("\nPassword Requirements:")
            report.append("✓ At least 8 characters")
            report.append("✓ At least one uppercase letter")
            report.append("✓ At least one lowercase letter")
            report.append("✓ At least one number")
            report.append("✓ No common patterns")
            
        if validation_result.get('gpt_credentials'):
            report.append("\nGPT Credentials Requirements:")
            report.append("✓ Username: 3-20 characters")
            report.append("✓ Username: Only letters and numbers")
            report.append("✓ Password: At least 6 characters")
            report.append("✓ No reserved words")
            
        return "\n".join(report)

    def get_progress_message(self, user_data: Dict[str, Any]) -> str:
        """Get registration progress message."""
        progress = []
        
        if user_data.get('username'):
            progress.append("✓ Username selected")
        else:
            progress.append("✗ Username not selected")
            
        if user_data.get('password'):
            progress.append("✓ Password set")
        else:
            progress.append("✗ Password not set")
            
        if user_data.get('gpt_username') and user_data.get('gpt_password'):
            progress.append("✓ GPT Credentials provided")
        else:
            progress.append("✗ GPT Credentials not provided")
            
        return "\n".join(progress)

    def format_error_message(self, error_type: str, error_message: str, step: str) -> str:
        """Format error message with remaining attempts."""
        remaining = self.get_remaining_attempts(step)
        time_remaining = self.get_time_remaining(step)
        
        if time_remaining:
            minutes = int(time_remaining.total_seconds() // 60)
            seconds = int(time_remaining.total_seconds() % 60)
            cooldown_message = f"\nPlease wait {minutes} minutes and {seconds} seconds before trying again."
        else:
            cooldown_message = ""
            
        return f"❌ {error_message}\n\n" \
               f"Remaining attempts: {remaining}\n" \
               f"{cooldown_message}"

    def get_step_description(self, step: str) -> str:
        """Get description for current step."""
        descriptions = {
            'username': "Please enter your desired username (3-20 characters, letters and numbers only)",
            'password': "Please enter a secure password (at least 8 characters with uppercase, lowercase, and numbers)",
            'gpt_credentials': "Please enter your GPT platform credentials in format: username|password",
            'confirmation': "Please confirm your registration details"
        }
        return descriptions.get(step, "Please follow the instructions")
