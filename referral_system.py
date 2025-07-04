import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
import secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReferralSystem:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize_db()

    def initialize_db(self):
        """Initialize referral tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create referrals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                referrer_id INTEGER,
                referred_id INTEGER,
                referral_code TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                PRIMARY KEY (referrer_id, referred_id)
            )
        ''')
        
        # Create referral bonuses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_bonuses (
                user_id INTEGER PRIMARY KEY,
                total_referrals INTEGER DEFAULT 0,
                successful_referrals INTEGER DEFAULT 0,
                total_bonus_points INTEGER DEFAULT 0,
                last_bonus TIMESTAMP
            )
        ''')
        
        # Create referral codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_codes (
                code TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def generate_referral_code(self, user_id: int) -> str:
        """Generate unique referral code for user."""
        while True:
            code = f"REF-{secrets.token_hex(3).upper()}"
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT 1 FROM referral_codes WHERE code = ?', (code,))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO referral_codes (code, user_id, expires_at)
                        VALUES (?, ?, datetime('now', '+30 days'))
                    ''', (code, user_id))
                    conn.commit()
                    return code
            except sqlite3.Error as e:
                logger.error(f"Error generating code: {str(e)}")
            finally:
                conn.close()

    def get_referral_code(self, user_id: int) -> Optional[str]:
        """Get user's referral code."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT code 
                FROM referral_codes 
                WHERE user_id = ? AND expires_at > CURRENT_TIMESTAMP
            ''', (user_id,))
            
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting code: {str(e)}")
            return None
        finally:
            conn.close()

    def validate_referral_code(self, code: str) -> Optional[int]:
        """Validate referral code and return user_id if valid."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT user_id 
                FROM referral_codes 
                WHERE code = ? AND expires_at > CURRENT_TIMESTAMP
            ''', (code,))
            
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Error validating code: {str(e)}")
            return None
        finally:
            conn.close()

    def record_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Record a successful referral."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if referral already exists
            cursor.execute('''
                SELECT 1 FROM referrals 
                WHERE referrer_id = ? AND referred_id = ?
            ''', (referrer_id, referred_id))
            
            if cursor.fetchone():
                return False
                
            # Record referral
            cursor.execute('''
                INSERT INTO referrals (referrer_id, referred_id, status)
                VALUES (?, ?, 'completed')
            ''', (referrer_id, referred_id))
            
            # Update referral bonuses
            cursor.execute('''
                INSERT OR REPLACE INTO referral_bonuses 
                (user_id, total_referrals, successful_referrals, total_bonus_points)
                VALUES 
                (?, 
                 COALESCE((SELECT total_referrals FROM referral_bonuses WHERE user_id = ?), 0) + 1,
                 COALESCE((SELECT successful_referrals FROM referral_bonuses WHERE user_id = ?), 0) + 1,
                 COALESCE((SELECT total_bonus_points FROM referral_bonuses WHERE user_id = ?), 0) + 5)
            ''', (referrer_id, referrer_id, referrer_id, referrer_id))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error recording referral: {str(e)}")
            return False
        finally:
            conn.close()

    def get_referral_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's referral statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get referral bonuses
            cursor.execute('''
                SELECT total_referrals, successful_referrals, total_bonus_points
                FROM referral_bonuses 
                WHERE user_id = ?
            ''', (user_id,))
            
            bonuses = cursor.fetchone()
            
            # Get recent referrals
            cursor.execute('''
                SELECT COUNT(*)
                FROM referrals 
                WHERE referrer_id = ? AND 
                      created_at >= date('now', '-7 days')
            ''', (user_id,))
            recent_referrals = cursor.fetchone()[0]
            
            return {
                'total_referrals': bonuses[0] if bonuses else 0,
                'successful_referrals': bonuses[1] if bonuses else 0,
                'total_bonus_points': bonuses[2] if bonuses else 0,
                'recent_referrals': recent_referrals,
                'referral_code': self.get_referral_code(user_id)
            }
        except sqlite3.Error as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {
                'total_referrals': 0,
                'successful_referrals': 0,
                'total_bonus_points': 0,
                'recent_referrals': 0,
                'referral_code': None
            }
        finally:
            conn.close()

    def get_top_referrers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top referrers by successful referrals."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT u.username, rb.successful_referrals, rb.total_bonus_points
                FROM referral_bonuses rb
                JOIN users u ON rb.user_id = u.id
                ORDER BY rb.successful_referrals DESC
                LIMIT ?
            ''', (limit,))
            
            return [{
                'username': row[0],
                'successful_referrals': row[1],
                'total_bonus_points': row[2]
            } for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting top referrers: {str(e)}")
            return []
        finally:
            conn.close()
