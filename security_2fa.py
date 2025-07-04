import os
import logging
import asyncio
from typing import Optional, Dict, Any
import hashlib
import hmac
import time
from datetime import datetime, timedelta
import json
import secrets
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import ChatNotFound

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security constants
TWO_FA_TIMEOUT = 300  # 5 minutes
TWO_FA_METHODS = ['email', 'sms', 'telegram', 'app']
MAX_ATTEMPTS = 3
MAX_FAILED_ATTEMPTS = 5
ATTEMPT_WINDOW = 3600  # 1 hour
SECRET_LENGTH = 32
CODE_LENGTH = 6

# 2FA configuration
TWO_FA_EMAIL = os.getenv('TWO_FA_EMAIL')
TWO_FA_EMAIL_API_KEY = os.getenv('TWO_FA_EMAIL_API_KEY')
TWO_FA_EMAIL_PROVIDER = os.getenv('TWO_FA_EMAIL_PROVIDER', 'sendgrid')
TWO_FA_SMS_API_KEY = os.getenv('TWO_FA_SMS_API_KEY')
TWO_FA_SMS_PROVIDER = os.getenv('TWO_FA_SMS_PROVIDER', 'twilio')
TWO_FA_APP_SECRET = os.getenv('TWO_FA_APP_SECRET')

# Email templates
EMAIL_SUBJECT = "2FA Code for TON Bot"
EMAIL_BODY = """Your 2FA code is: {code}
This code will expire in 5 minutes.
Do not share this code with anyone.
"""

# SMS templates
SMS_BODY = """Your 2FA code is: {code}
This code will expire in 5 minutes.
Do not share this code with anyone.
"""

# App configuration
APP_NAME = "TON Bot 2FA"
ISSUER = "TON Bot"
QR_CODE_SIZE = 200

class TwoFactorAuth:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize_db()
        self.session = None
        self.lock = asyncio.Lock()
        
    def initialize_db(self):
        """Initialize 2FA tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create 2FA table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS two_fa (
                user_id INTEGER PRIMARY KEY,
                method TEXT,
                secret TEXT,
                enabled BOOLEAN DEFAULT FALSE,
                last_code TEXT,
                last_code_time TIMESTAMP,
                last_ip TEXT,
                last_attempt TIMESTAMP,
                failed_attempts INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Create 2FA attempts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS two_fa_attempts (
                user_id INTEGER,
                attempt_time TIMESTAMP,
                success BOOLEAN,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Create 2FA sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS two_fa_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()

    async def setup_2fa(self, user_id: int, method: str, update: types.Update = None) -> Dict[str, Any]:
        """Setup 2FA for user."""
        try:
            if method not in TWO_FA_METHODS:
                raise ValueError(f"Invalid 2FA method: {method}")
                
            async with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Generate secret
                secret = secrets.token_hex(SECRET_LENGTH)
                
                # Update or insert 2FA record
                cursor.execute('''
                    INSERT OR REPLACE INTO two_fa 
                    (user_id, method, secret, enabled, last_ip)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, method, secret, False, update.effective_message.chat.id if update else None))
                
                conn.commit()
                
                # Send setup instructions based on method
                result = {
                    'success': True,
                    'method': method,
                    'secret': secret
                }
                
                if method == 'email':
                    # Send email with setup instructions
                    email = await self.get_user_email(user_id)
                    if email:
                        await self.send_email(email, EMAIL_SUBJECT, EMAIL_BODY.format(secret=secret))
                        result['message'] = "Setup instructions sent to your email"
                elif method == 'sms':
                    # Send SMS with setup instructions
                    phone = await self.get_user_phone(user_id)
                    if phone:
                        await self.send_sms(phone, SMS_BODY.format(secret=secret))
                        result['message'] = "Setup instructions sent to your phone"
                elif method == 'telegram':
                    # Send Telegram message
                    try:
                        await bot.send_message(
                            user_id,
                            "2FA setup complete!\n\n"
                            f"Your secret: {secret}\n\n"
                            "Please save this secret securely."
                        )
                        result['message'] = "Setup instructions sent via Telegram"
                    except ChatNotFound:
                        raise Exception("User not found")
                elif method == 'app':
                    # Generate QR code for authenticator app
                    import qrcode
                    from io import BytesIO
                    
                    otpauth_url = f"otpauth://totp/{ISSUER}:{user_id}?secret={secret}&issuer={APP_NAME}"
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(otpauth_url)
                    qr.make(fit=True)
                    
                    img = qr.make_image(fill_color="black", back_color="white")
                    buffer = BytesIO()
                    img.save(buffer, format="PNG")
                    buffer.seek(0)
                    
                    # Send QR code
                    await bot.send_photo(
                        user_id,
                        photo=buffer,
                        caption="Scan this QR code with your authenticator app"
                    )
                    result['message'] = "QR code sent for authenticator app setup"
                
                return result
                
        except Exception as e:
            logger.error(f"Error setting up 2FA: {str(e)}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    async def get_user_email(self, user_id: int) -> Optional[str]:
        """Get user's email from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT email FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting user email: {str(e)}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    async def get_user_phone(self, user_id: int) -> Optional[str]:
        """Get user's phone from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT phone FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting user phone: {str(e)}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    async def send_email(self, email: str, subject: str, body: str) -> bool:
        """Send email using configured provider."""
        try:
            if TWO_FA_EMAIL_PROVIDER == 'sendgrid':
                import sendgrid
                from sendgrid.helpers.mail import Mail
                
                sg = sendgrid.SendGridAPIClient(api_key=TWO_FA_EMAIL_API_KEY)
                message = Mail(
                    from_email=TWO_FA_EMAIL,
                    to_emails=email,
                    subject=subject,
                    plain_text_content=body
                )
                response = sg.send(message)
                return response.status_code == 202
            return False
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False

    async def send_sms(self, phone: str, body: str) -> bool:
        """Send SMS using configured provider."""
        try:
            if TWO_FA_SMS_PROVIDER == 'twilio':
                from twilio.rest import Client
                
                client = Client(
                    os.getenv('TWILIO_ACCOUNT_SID'),
                    os.getenv('TWILIO_AUTH_TOKEN')
                )
                
                message = client.messages.create(
                    body=body,
                    from_=os.getenv('TWILIO_PHONE_NUMBER'),
                    to=phone
                )
                return message.sid is not None
            return False
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False

    async def generate_2fa_code(self, user_id: int, method: str = None) -> Dict[str, Any]:
        """Generate 2FA code and send it via configured method."""
        try:
            async with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get user's secret and method
                cursor.execute('''
                    SELECT secret, method 
                    FROM two_fa 
                    WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                if not result:
                    raise Exception("2FA not set up")
                    
                secret, user_method = result
                
                # If method not specified, use user's preferred method
                if not method:
                    method = user_method
                
                # Generate code
                timestamp = int(time.time()) // 30
                code = hashlib.sha256(
                    f"{secret}{timestamp}".encode()
                ).hexdigest()[:CODE_LENGTH]
                
                # Store code
                cursor.execute('''
                    UPDATE two_fa 
                    SET last_code = ?, 
                        last_code_time = ?,
                        last_ip = ?
                    WHERE user_id = ?
                ''', (
                    code,
                    datetime.now(),
                    None,  # IP will be set when code is verified
                    user_id
                ))
                
                conn.commit()
                
                # Send code based on method
                result = {'code': code, 'method': method}
                
                if method == 'email':
                    email = await self.get_user_email(user_id)
                    if email:
                        await self.send_email(email, EMAIL_SUBJECT, EMAIL_BODY.format(code=code))
                        result['message'] = "Code sent to your email"
                elif method == 'sms':
                    phone = await self.get_user_phone(user_id)
                    if phone:
                        await self.send_sms(phone, SMS_BODY.format(code=code))
                        result['message'] = "Code sent to your phone"
                elif method == 'telegram':
                    try:
                        await bot.send_message(
                            user_id,
                            f"Your 2FA code: {code}\n\n"
                            "This code will expire in 5 minutes."
                        )
                        result['message'] = "Code sent via Telegram"
                    except ChatNotFound:
                        raise Exception("User not found")
                elif method == 'app':
                    result['message'] = "Code generated for authenticator app"
                
                return result
                
        except Exception as e:
            logger.error(f"Error generating 2FA code: {str(e)}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    async def verify_2fa_code(self, user_id: int, code: str, ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Verify 2FA code with additional security checks."""
        try:
            async with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Check rate limiting
                if not await self.check_2fa_attempts(user_id):
                    raise Exception("Too many failed attempts. Please try again later.")
                
                # Get stored code and details
                cursor.execute('''
                    SELECT last_code, last_code_time, last_ip, failed_attempts 
                    FROM two_fa 
                    WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                
                if not result:
                    raise Exception("2FA not set up")
                    
                stored_code, code_time, last_ip, failed_attempts = result
                
                # Check if code is expired
                if (datetime.now() - datetime.fromisoformat(code_time)).total_seconds() > TWO_FA_TIMEOUT:
                    raise Exception("2FA code expired")
                    
                # Check for IP change
                if last_ip and ip_address and last_ip != ip_address:
                    raise Exception("IP address mismatch")
                    
                # Verify code
                if code == stored_code:
                    # Record successful attempt
                    cursor.execute('''
                        INSERT INTO two_fa_attempts 
                        (user_id, attempt_time, success, ip_address, user_agent)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, datetime.now(), True, ip_address, user_agent))
                    
                    # Reset failed attempts
                    cursor.execute('''
                        UPDATE two_fa 
                        SET failed_attempts = 0,
                            last_ip = ?
                        WHERE user_id = ?
                    ''', (ip_address, user_id))
                    
                    conn.commit()
                    return {
                        'success': True,
                        'message': '2FA code verified successfully'
                    }
                    
                # Record failed attempt
                cursor.execute('''
                    INSERT INTO two_fa_attempts 
                    (user_id, attempt_time, success, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, datetime.now(), False, ip_address, user_agent))
                
                # Increment failed attempts
                cursor.execute('''
                    UPDATE two_fa 
                    SET failed_attempts = failed_attempts + 1,
                        last_ip = ?
                    WHERE user_id = ?
                ''', (ip_address, user_id))
                
                conn.commit()
                
                # Check if account is locked
                if failed_attempts >= MAX_FAILED_ATTEMPTS:
                    raise Exception("Account locked due to too many failed attempts")
                    
                return {
                    'success': False,
                    'message': 'Invalid 2FA code'
                }
                
        except Exception as e:
            logger.error(f"Error verifying 2FA code: {str(e)}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    async def check_2fa_attempts(self, user_id: int) -> Dict[str, Any]:
        """Check 2FA attempts and return detailed status."""
        try:
            async with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get failed attempts in last hour
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM two_fa_attempts 
                    WHERE user_id = ? 
                    AND attempt_time > ? 
                    AND success = ?
                ''', (
                    user_id,
                    datetime.now() - timedelta(hours=1),
                    False
                ))
                
                failed_attempts = cursor.fetchone()[0]
                
                # Get last failed attempts
                cursor.execute('''
                    SELECT attempt_time, ip_address, user_agent 
                    FROM two_fa_attempts 
                    WHERE user_id = ? 
                    AND success = ? 
                    ORDER BY attempt_time DESC 
                    LIMIT 5
                ''', (user_id, False))
                
                last_attempts = cursor.fetchall()
                
                result = {
                    'attempts': failed_attempts,
                    'max_attempts': MAX_ATTEMPTS,
                    'window': ATTEMPT_WINDOW,
                    'locked': failed_attempts >= MAX_ATTEMPTS,
                    'last_attempts': [
                        {
                            'time': attempt[0],
                            'ip': attempt[1],
                            'user_agent': attempt[2]
                        } for attempt in last_attempts
                    ]
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Error checking 2FA attempts: {str(e)}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    async def create_2fa_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Create 2FA method selection keyboard with detailed options."""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        # Get current method and status
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT method, enabled, failed_attempts 
            FROM two_fa 
            WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        current_method = result[0] if result else None
        enabled = result[1] if result else False
        failed_attempts = result[2] if result else 0
        
        # Add method selection buttons
        for method in TWO_FA_METHODS:
            text = f"{method.title()} ✅" if current_method == method else method.title()
            keyboard.add(
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"2fa_method_{method}"
                )
            )
        
        # Add status buttons
        status_buttons = []
        if enabled:
            status_buttons.append(
                InlineKeyboardButton(
                    text="✅ Enabled",
                    callback_data="2fa_status_enabled"
                )
            )
        else:
            status_buttons.append(
                InlineKeyboardButton(
                    text="❌ Disabled",
                    callback_data="2fa_status_disabled"
                )
            )
            
        if failed_attempts > 0:
            status_buttons.append(
                InlineKeyboardButton(
                    text=f"⚠️ {failed_attempts} Failed Attempts",
                    callback_data="2fa_attempts"
                )
            )
            
        if status_buttons:
            keyboard.row(*status_buttons)
        
        return keyboard

# Initialize 2FA system
two_fa = TwoFactorAuth("botdata.db")
