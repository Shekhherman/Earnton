import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
import hashlib
import hmac
import time
from datetime import datetime, timedelta
import json
import aiohttp
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from collections import defaultdict
import threading
import schedule

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Analytics and monitoring
ANALYTICS_INTERVAL = 300  # 5 minutes
MAX_FAILED_ATTEMPTS = 3
RATE_LIMIT_WINDOW = 3600  # 1 hour

# Payment analytics
payment_analytics = {
    'total_payments': 0,
    'successful_payments': 0,
    'failed_payments': 0,
    'total_amount': 0.0,
    'average_amount': 0.0,
    'daily_stats': defaultdict(int),
    'payment_methods': defaultdict(int)
}

# Rate limiting
rate_limits = defaultdict(int)
failed_attempts = defaultdict(int)

# Monitoring thread
class MonitoringThread(threading.Thread):
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.daemon = True

    def run(self):
        while True:
            try:
                # Update analytics
                self.update_analytics()
                
                # Check for suspicious activity
                self.check_suspicious_activity()
                
                # Clean up old data
                self.cleanup_old_data()
                
            except Exception as e:
                logger.error(f"Monitoring error: {str(e)}")
            
            time.sleep(ANALYTICS_INTERVAL)

    def update_analytics(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update payment statistics
        cursor.execute('SELECT COUNT(*), SUM(amount) FROM payments')
        total, total_amount = cursor.fetchone()
        payment_analytics['total_payments'] = total
        payment_analytics['total_amount'] = total_amount or 0
        
        cursor.execute('SELECT COUNT(*) FROM payments WHERE status = ?', ('confirmed',))
        payment_analytics['successful_payments'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM payments WHERE status = ?', ('failed',))
        payment_analytics['failed_payments'] = cursor.fetchone()[0]
        
        if total > 0:
            payment_analytics['average_amount'] = total_amount / total
        
        # Update daily stats
        today = datetime.now().strftime('%Y-%m-%d')
        payment_analytics['daily_stats'][today] += 1
        
        conn.close()

    def check_suspicious_activity(self):
        global rate_limits, failed_attempts
        
        # Check for rate limiting violations
        current_time = time.time()
        for user_id, count in rate_limits.items():
            if count > MAX_REQUESTS_PER_MINUTE:
                logger.warning(f"Rate limit violation detected for user {user_id}")
                
        # Check for failed payment attempts
        for user_id, count in failed_attempts.items():
            if count > MAX_FAILED_ATTEMPTS:
                logger.warning(f"Suspicious activity detected for user {user_id}: {count} failed attempts")
                
        # Clean up old data
        for user_id in list(rate_limits.keys()):
            if current_time - rate_limits[user_id] > RATE_LIMIT_WINDOW:
                del rate_limits[user_id]
                
        for user_id in list(failed_attempts.keys()):
            if current_time - failed_attempts[user_id] > RATE_LIMIT_WINDOW:
                del failed_attempts[user_id]

    def cleanup_old_data(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Remove expired payments
        cursor.execute('''
            DELETE FROM payments 
            WHERE expires_at < ? AND status = ?
        ''', (datetime.now(), 'expired'))
        
        # Remove old analytics data
        cutoff_date = datetime.now() - timedelta(days=30)
        cursor.execute('''
            DELETE FROM advertisements 
            WHERE created_at < ? AND status = ?
        ''', (cutoff_date, 'expired'))
        
        conn.commit()
        conn.close()

# Start monitoring thread
monitoring_thread = MonitoringThread("botdata.db")
monitoring_thread.start()

# TON API configuration
TON_API_URL = "https://api.ton.org/v1"
TON_WALLET = os.getenv('TON_WALLET_ADDRESS')
TON_API_KEY = os.getenv('TON_API_KEY')

# Payment constants
MIN_PAYMENT_AMOUNT = 0.1  # Minimum payment in TON
PAYMENT_TIMEOUT = 300  # 5 minutes in seconds

# Payment status
PAYMENT_STATUS = {
    'pending': '⏳ Pending',
    'confirmed': '✅ Confirmed',
    'expired': '❌ Expired',
    'failed': '❌ Failed'
}

class TONPayment:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize_db()
        self.session = aiohttp.ClientSession()
        self.lock = asyncio.Lock()
        
    async def get_payment_analytics(self) -> Dict[str, Any]:
        """Get payment analytics."""
        return {
            'total_payments': payment_analytics['total_payments'],
            'successful_payments': payment_analytics['successful_payments'],
            'failed_payments': payment_analytics['failed_payments'],
            'total_amount': payment_analytics['total_amount'],
            'average_amount': payment_analytics['average_amount'],
            'daily_stats': dict(payment_analytics['daily_stats']),
            'payment_methods': dict(payment_analytics['payment_methods'])
        }

    async def check_suspicious_activity(self, user_id: int) -> bool:
        """Check for suspicious activity."""
        current_time = time.time()
        
        # Check rate limits
        if rate_limits[user_id] > MAX_REQUESTS_PER_MINUTE:
            return True
            
        # Check failed attempts
        if failed_attempts[user_id] > MAX_FAILED_ATTEMPTS:
            return True
            
        # Reset counters if within window
        if current_time - rate_limits[user_id] > RATE_LIMIT_WINDOW:
            rate_limits[user_id] = 0
            failed_attempts[user_id] = 0
            
        return False

    async def create_payment_address(self, user_id: int, amount: float) -> Dict[str, Any]:
        """Create a new payment address for user."""
        try:
            # Check for suspicious activity
            if await self.check_suspicious_activity(user_id):
                raise Exception("Suspicious activity detected")
                
            # Increment rate limit counter
            rate_limits[user_id] += 1
            
            # Validate amount
            if amount < MIN_PAYMENT_AMOUNT:
                raise ValueError(f"Minimum payment amount is {MIN_PAYMENT_AMOUNT} TON")

            # Create payment record
            async with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Generate unique payment ID
                payment_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:10]
                
                # Create payment record
                cursor.execute('''
                    INSERT INTO payments (user_id, amount, status, payment_address, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    amount,
                    'pending',
                    payment_id,
                    datetime.now(),
                    datetime.now() + timedelta(seconds=PAYMENT_TIMEOUT)
                ))
                
                conn.commit()
                payment_id = cursor.lastrowid
                
                # Create payment address
                async with self.session.post(
                    f"{TON_API_URL}/createPaymentAddress",
                    headers={'Authorization': f'Bearer {TON_API_KEY}'},
                    json={
                        'amount': amount,
                        'lifetime': PAYMENT_TIMEOUT
                    }
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to create payment address: {response.status}")
                    
                    data = await response.json()
                    payment_address = data['address']
                    
                    # Update payment record with address
                    cursor.execute('UPDATE payments SET payment_address = ? WHERE id = ?', 
                                 (payment_address, payment_id))
                    conn.commit()
                
                return {
                    'payment_id': payment_id,
                    'amount': amount,
                    'address': payment_address,
                    'expires_at': (datetime.now() + timedelta(seconds=PAYMENT_TIMEOUT)).isoformat()
                }
                
        except Exception as e:
            # Increment failed attempts
            failed_attempts[user_id] += 1
            logger.error(f"Error creating payment address: {str(e)}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    def initialize_db(self):
        """Initialize payment tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create payments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                status TEXT,
                payment_address TEXT,
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Create advertisements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS advertisements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_id INTEGER,
                title TEXT,
                description TEXT,
                media_url TEXT,
                status TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (payment_id) REFERENCES payments(id)
            )
        ''')
        
        conn.commit()
        conn.close()

    async def create_payment_address(self, user_id: int, amount: float) -> Dict[str, Any]:
        """Create a new payment address for user."""
        try:
            # Validate amount
            if amount < MIN_PAYMENT_AMOUNT:
                raise ValueError(f"Minimum payment amount is {MIN_PAYMENT_AMOUNT} TON")

            # Create payment record
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Generate unique payment ID
            payment_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:10]
            
            # Create payment record
            cursor.execute('''
                INSERT INTO payments (user_id, amount, status, payment_address, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                amount,
                'pending',
                payment_id,
                datetime.now(),
                datetime.now() + timedelta(seconds=PAYMENT_TIMEOUT)
            ))
            
            conn.commit()
            payment_id = cursor.lastrowid
            
            # Create payment address
            async with self.session.post(
                f"{TON_API_URL}/createPaymentAddress",
                headers={'Authorization': f'Bearer {TON_API_KEY}'},
                json={
                    'amount': amount,
                    'lifetime': PAYMENT_TIMEOUT
                }
            ) as response:
                if response.status != 200:
                    raise Exception(f"Failed to create payment address: {response.status}")
                
                data = await response.json()
                payment_address = data['address']
                
                # Update payment record with address
                cursor.execute('UPDATE payments SET payment_address = ? WHERE id = ?', 
                             (payment_address, payment_id))
                conn.commit()
            
            return {
                'payment_id': payment_id,
                'amount': amount,
                'address': payment_address,
                'expires_at': (datetime.now() + timedelta(seconds=PAYMENT_TIMEOUT)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating payment address: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    async def check_payment_status(self, payment_id: int) -> Dict[str, Any]:
        """Check payment status."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_id,))
            payment = cursor.fetchone()
            
            if not payment:
                raise ValueError("Payment not found")
            
            payment_data = {
                'id': payment[0],
                'user_id': payment[1],
                'amount': payment[2],
                'status': payment[3],
                'address': payment[4],
                'created_at': payment[5],
                'expires_at': payment[6]
            }
            
            # Check if payment has expired
            if datetime.fromisoformat(payment[6]) < datetime.now():
                if payment[3] == 'pending':
                    cursor.execute('UPDATE payments SET status = ? WHERE id = ?', 
                                 ('expired', payment_id))
                    conn.commit()
                    payment_data['status'] = 'expired'
                return payment_data
            
            # Check payment status on TON network
            async with self.session.get(
                f"{TON_API_URL}/getPaymentStatus",
                headers={'Authorization': f'Bearer {TON_API_KEY}'},
                params={'address': payment[4]}
            ) as response:
                if response.status != 200:
                    raise Exception(f"Failed to check payment status: {response.status}")
                
                data = await response.json()
                
                if data['status'] == 'confirmed':
                    cursor.execute('UPDATE payments SET status = ? WHERE id = ?', 
                                 ('confirmed', payment_id))
                    conn.commit()
                    payment_data['status'] = 'confirmed'
                
            return payment_data
            
        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    async def create_advertisement(self, user_id: int, payment_id: int, title: str, description: str, media_url: str) -> int:
        """Create a new advertisement."""
        try:
            # Validate payment status
            payment = await self.check_payment_status(payment_id)
            if payment['status'] != 'confirmed':
                raise ValueError("Payment not confirmed")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO advertisements (user_id, payment_id, title, description, media_url, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                payment_id,
                title,
                description,
                media_url,
                'active'
            ))
            
            conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"Error creating advertisement: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    async def get_advertisements(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of advertisements."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('SELECT * FROM advertisements WHERE user_id = ?', (user_id,))
            else:
                cursor.execute('SELECT * FROM advertisements WHERE status = ?', ('active',))
            
            ads = []
            for ad in cursor.fetchall():
                ads.append({
                    'id': ad[0],
                    'user_id': ad[1],
                    'title': ad[3],
                    'description': ad[4],
                    'media_url': ad[5],
                    'status': ad[6],
                    'created_at': ad[7]
                })
            
            return ads
            
        except Exception as e:
            logger.error(f"Error getting advertisements: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    async def create_payment_keyboard(self, payment_id: int) -> InlineKeyboardMarkup:
        """Create keyboard with payment status button."""
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                text="Check Payment Status",
                callback_data=f"check_payment_{payment_id}"
            )
        )
        return keyboard

# Initialize TON payment system
ton_payment = TONPayment("botdata.db")
