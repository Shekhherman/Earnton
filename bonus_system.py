import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

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

    def get_daily_bonus(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Check if user can claim daily bonus.
        
        Returns:
            dict: Bonus info if available, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT * FROM daily_bonuses WHERE user_id = ? AND date = ?', 
                     (user_id, today))
        
        if cursor.fetchone():
            conn.close()
            return None
            
        cursor.execute('SELECT date FROM daily_bonuses WHERE user_id = ? 
                      ORDER BY date DESC LIMIT 1', (user_id,))
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

    def claim_daily_bonus(self, user_id: int) -> bool:
        """
        Claim daily bonus for user.
        
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        try:
            cursor.execute('INSERT INTO daily_bonuses (user_id, date, points) VALUES (?, ?, ?)',
                         (user_id, today, self.daily_bonus))
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
