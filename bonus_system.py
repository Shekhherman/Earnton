import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from functools import wraps
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security constants
MAX_DAILY_BONUS = 100
MAX_REFERRAL_BONUS = 50
BONUS_COOLDOWN = 86400  # 24 hours
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Rate limiting decorator
def rate_limited(max_calls: int = 100, period: int = 3600):
    """Rate limit decorator."""
    def decorator(func):
        calls = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = args[1] if len(args) > 1 else kwargs.get('user_id')
            if not user_id:
                raise ValueError("User ID is required")
            
            now = time.time()
            if user_id not in calls:
                calls[user_id] = []
            
            # Remove old calls
            calls[user_id] = [t for t in calls[user_id] if now - t < period]
            
            if len(calls[user_id]) >= max_calls:
                raise Exception("Rate limit exceeded")
            
            calls[user_id].append(now)
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

class BonusSystem:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.daily_bonus = 10  # Points for daily bonus
        self.referral_bonus = 5  # Points for successful referral
        self.initialize_db()

    def initialize_db(self):
        """Initialize bonus tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create daily bonus table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_bonuses (
                user_id INTEGER,
                date TEXT,
                points INTEGER,
                PRIMARY KEY (user_id, date)
            )
        ''')
        
        # Create referrals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                referrer_id INTEGER,
                referred_id INTEGER,
                date TEXT,
                PRIMARY KEY (referrer_id, referred_id)
            )
        ''')
        
        conn.commit()
        conn.close()

    @rate_limited(max_calls=10, period=3600)
    async def get_daily_bonus(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Check if user can claim daily bonus with security checks.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            dict: Bonus info if available, None otherwise
            
        Raises:
            ValueError: If user_id is invalid
            Exception: If rate limit is exceeded
        """
        try:
            # Validate user_id
            if not isinstance(user_id, int):
                raise ValueError("Invalid user_id")
                
            # Check if user exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users WHERE id = ?', (user_id,))
            if not cursor.fetchone()[0]:
                raise ValueError("User not found")
                
            # Check last bonus claim
            cursor.execute('''
                SELECT date 
                FROM daily_bonuses 
                WHERE user_id = ? 
                ORDER BY date DESC 
                LIMIT 1
            ''', (user_id,))
            
            last_claim = cursor.fetchone()
            if last_claim:
                last_claim_date = datetime.strptime(last_claim[0], '%Y-%m-%d')
                if (datetime.now() - last_claim_date).total_seconds() < BONUS_COOLDOWN:
                    return None
            
            return {
                'points': self.daily_bonus,
                'next_claim': (datetime.now() + timedelta(seconds=BONUS_COOLDOWN)).isoformat()
            }
            
        except sqlite3.Error as e:
            logger.error(f"Database error in get_daily_bonus: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in get_daily_bonus: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
        
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT * FROM daily_bonuses WHERE user_id = ? AND date = ?', 
                     (user_id, today))
        
        if cursor.fetchone():
            conn.close()
            return None
            
        cursor.execute('SELECT date FROM daily_bonuses WHERE user_id = ? ORDER BY date DESC LIMIT 1', (user_id,))
        last_bonus = cursor.fetchone()
        
        if last_bonus:
            last_date = datetime.strptime(last_bonus[0], '%Y-%m-%d')
            days_since = (datetime.now() - last_date).days
            if days_since < 1:
                conn.close()
                return None

        conn.close()
        return {
            'points': self.daily_bonus,
            'next_available': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        }

    @rate_limited(max_calls=5, period=3600)
    async def claim_daily_bonus(self, user_id: int) -> bool:
        """
        Claim daily bonus for user with security checks.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if bonus was claimed, False otherwise
            
        Raises:
            ValueError: If user_id is invalid
            Exception: If rate limit is exceeded
            Exception: If bonus cannot be claimed
        """
        try:
            # Validate user_id
            if not isinstance(user_id, int):
                raise ValueError("Invalid user_id")
                
            # Check if user exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users WHERE id = ?', (user_id,))
            if not cursor.fetchone()[0]:
                raise ValueError("User not found")
                
            # Check last bonus claim
            cursor.execute('''
                SELECT date 
                FROM daily_bonuses 
                WHERE user_id = ? 
                ORDER BY date DESC 
                LIMIT 1
            ''', (user_id,))
            
            last_claim = cursor.fetchone()
            if last_claim:
                last_claim_date = datetime.strptime(last_claim[0], '%Y-%m-%d')
                if (datetime.now() - last_claim_date).total_seconds() < BONUS_COOLDOWN:
                    raise Exception("Bonus cooldown not reached")
            
            # Claim bonus
            cursor.execute('''
                INSERT INTO daily_bonuses (user_id, date, points)
                VALUES (?, ?, ?)
            ''', (user_id, datetime.now().strftime('%Y-%m-%d'), self.daily_bonus))
            
            # Update user points
            cursor.execute('''
                UPDATE users 
                SET points = points + ? 
                WHERE id = ?
            ''', (self.daily_bonus, user_id))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        """
        Add a referral.
        
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        try:
            cursor.execute('INSERT INTO referrals (referrer_id, referred_id, date) VALUES (?, ?, ?)',
                         (referrer_id, referred_id, today))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_referral_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get referral statistics for user.
        
        Returns:
            dict: Referral statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
        total_referrals = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND date >= date("now", "-7 days")', 
                     (user_id,))
        weekly_referrals = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND date >= date("now", "-30 days")', 
                     (user_id,))
        monthly_referrals = cursor.fetchone()[0]
        
        conn.close()
        return {
            'total': total_referrals,
            'weekly': weekly_referrals,
            'monthly': monthly_referrals,
            'bonus_points': total_referrals * self.referral_bonus
        }
