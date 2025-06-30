import os
import sys
import logging
from dotenv import load_dotenv
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand, Update, Message, CallbackQuery
from aiogram.filters import Command, Text
from aiohttp import ClientSession
from security_middleware import security_middleware
import hmac
import hashlib
import secrets
import time
import sys
from typing import Dict, Optional

# Security constants
MAX_REQUESTS_PER_MINUTE = 60  # 60 requests per minute
REQUEST_WINDOW = 60  # 1 minute window
MAX_MESSAGE_LENGTH = 4096  # Telegram's max message length
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
MAX_CONCURRENT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60  # 1 minute
MAX_FAILED_ATTEMPTS = 5
FAILED_ATTEMPT_WINDOW = 3600  # 1 hour
MAX_SESSION_DURATION = 3600  # 1 hour
SESSION_CLEANUP_INTERVAL = 3600  # 1 hour
MAX_IP_REQUESTS = 100  # 100 requests per IP
IP_REQUEST_WINDOW = 3600  # 1 hour
MAX_USER_REQUESTS = 1000  # 1000 requests per user
USER_REQUEST_WINDOW = 86400  # 24 hours

# Security headers
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-src 'none'; object-src 'none'; media-src 'self' data:; font-src 'self' data:; form-action 'self'; frame-ancestors 'none'; navigate-to 'self'; report-uri '/csp-report'",
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',  # 1 year
    'X-Permitted-Cross-Domain-Policies': 'none',
    'X-Download-Options': 'noopen',
    'Expect-CT': 'max-age=86400, enforce, report-uri="https://example.com/report"',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
    'Feature-Policy': 'geolocation=\'none\'; microphone=\'none\'; camera=\'none\';',
    'DNS-Prefetch-Control': 'off'
}

# Security configuration
SECURITY_CONFIG = {
    # Rate limiting
    'rate_limit': {
        'global': {
            'requests': MAX_REQUESTS_PER_MINUTE,
            'window': REQUEST_WINDOW,
            'adaptive': True,
            'threshold': 0.8,
            'increase_factor': 1.5,
            'decrease_factor': 0.5
        },
        'ip': {
            'requests': MAX_IP_REQUESTS,
            'window': IP_REQUEST_WINDOW,
            'device_fingerprinting': True,
            'geo_location': True
        },
        'user': {
            'requests': MAX_USER_REQUESTS,
            'window': USER_REQUEST_WINDOW,
            'behavior_analysis': True,
            'time_based': True
        },
        'device': {
            'requests': 100,
            'window': 3600,
            'fingerprinting': True
        }
    },
    
    # Authentication
    'authentication': {
        '2fa': {
            'enabled': True,
            'methods': ['app', 'email', 'sms', 'telegram'],
            'timeout': 300,
            'max_attempts': 3
        },
        'device_verification': {
            'enabled': True,
            'timeout': 300,
            'max_attempts': 3
        },
        'location_verification': {
            'enabled': True,
            'max_distance': 1000,
            'timeout': 300
        }
    },
    
    # Input validation
    'input_validation': {
        'sql_injection': {
            'enabled': True,
            'patterns': [
                '--', ';', '/*', '*/', 'xp_', 'exec', 'union', 'select', 'insert', 'update', 'delete'
            ]
        },
        'xss': {
            'enabled': True,
            'patterns': [
                '<script', 'javascript:', 'onload=', 'onerror=', 'onclick=', 'eval(',
                'document.cookie', 'window.location', 'alert('
            ]
        },
        'command_injection': {
            'enabled': True,
            'patterns': [
                ';', '&', '|', '&&', '||', '>', '<', '>>', '<<', '2>', '2>>', '2>&1'
            ]
        },
        'file_injection': {
            'enabled': True,
            'patterns': [
                '../', './', '/etc/passwd', '/etc/shadow', '/root', '/home', 'C:\\'
            ]
        }
    },
    
    # Security headers
    'security_headers': {
        'content_security_policy': {
            'enabled': True,
            'policy': {
                'default-src': "'none'",
                'script-src': "'self' 'unsafe-inline'",
                'style-src': "'self' 'unsafe-inline'",
                'img-src': "'self' data:",
                'connect-src': "'self'",
                'frame-src': "'none'",
                'object-src': "'none'",
                'media-src': "'self' data:",
                'font-src': "'self' data:",
                'form-action': "'self'",
                'frame-ancestors': "'none'",
                'navigate-to': "'self'",
                'report-uri': '/csp-report'
            }
        },
        'additional': {
            **SECURITY_HEADERS,
            'DNS-Prefetch-Control': 'off'
        }
    },
    
    # Logging
    'logging': {
        'enabled': True,
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'handlers': {
            'file': {
                'filename': 'security.log',
                'max_bytes': 10485760,
                'backup_count': 5
            },
            'syslog': {
                'enabled': True,
                'address': '/dev/log'
            }
        },
        'events': {
            'request': True,
            'response': True,
            'error': True,
            'access': True,
            'security': True
        }
    },
    
    # Monitoring
    'monitoring': {
        'enabled': True,
        'anomaly_detection': {
            'threshold': 3,
            'window': 3600,
            'patterns': {
                'rate': 1.5,
                'pattern': 0.8,
                'location': 0.5
            }
        },
        'threat_detection': {
            'enabled': True,
            'providers': ['ipinfo', 'virustotal'],
            'update_interval': 3600
        },
        'real_time': {
            'enabled': True,
            'interval': 5,
            'threshold': 10
        }
    },
    
    # Data protection
    'data_protection': {
        'encryption': {
            'enabled': True,
            'algorithm': 'AES-256-CBC',
            'key_length': 32,
            'iv_length': 16
        },
        'tokenization': {
            'enabled': True,
            'algorithms': ['jwt', 'hmac'],
            'token_lifetime': 3600
        },
        'masking': {
            'enabled': True,
            'patterns': {
                'credit_card': 'XXXX-XXXX-XXXX-XXXX',
                'phone': '+XX (XXX) XXX-XX-XX',
                'email': 'user@domain.com'
            }
        }
    },
    
    # Access control
    'access_control': {
        'role_based': {
            'enabled': True,
            'roles': {
                'admin': ['*'],
                'user': ['read', 'write'],
                'guest': ['read']
            }
        },
        'attribute_based': {
            'enabled': True,
            'attributes': {
                'location': True,
                'time': True,
                'device': True
            }
        },
        'time_based': {
            'enabled': True,
            'rules': {
                'working_hours': {
                    'start': '09:00',
                    'end': '17:00',
                    'days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                }
            }
        }
    },
    
    # Security scanning
    'scanning': {
        'vulnerability': {
            'enabled': True,
            'providers': ['nvd', 'cve'],
            'update_interval': 3600
        },
        'malware': {
            'enabled': True,
            'providers': ['virustotal', 'clamav'],
            'update_interval': 3600
        },
        'content': {
            'enabled': True,
            'providers': ['google_safe_browsing', 'phish_tank'],
            'update_interval': 3600
        }
    },
    
    # Security response
    'security_response': {
        'blocking': {
            'enabled': True,
            'threshold': 10,
            'duration': 3600
        },
        'rate_limiting': {
            'enabled': True,
            'threshold': 1.5,
            'duration': 300
        },
        'notifications': {
            'enabled': True,
            'providers': ['email', 'sms', 'telegram'],
            'threshold': 5
        },
        'emergency': {
            'enabled': True,
            'threshold': 50,
            'actions': ['shutdown', 'block', 'alert']
        }
    }
}

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get bot token from environment
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
    sys.exit(1)

# Initialize bot with security settings
bot = Bot(
    token=BOT_TOKEN,
    parse_mode='HTML',
    validate_token=True
)

dp = Dispatcher(bot)

# Rate limiting middleware
class RateLimiter:
    def __init__(self):
        self.requests = {}
        self.lock = asyncio.Lock()

    async def process_update(self, update: Update):
        user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
        
        async with self.lock:
            if user_id not in self.requests:
                self.requests[user_id] = []
            
            # Remove old requests
            current_time = time.time()
            self.requests[user_id] = [t for t in self.requests[user_id] if current_time - t < 60]
            
            if len(self.requests[user_id]) >= MAX_REQUESTS_PER_MINUTE:
                raise Exception("Rate limit exceeded")
            
            self.requests[user_id].append(current_time)

# Initialize rate limiter
rate_limiter = RateLimiter()

# Security middleware
dp.middleware.setup(rate_limiter)

# Message validation middleware
class MessageValidator:
    def __init__(self):
        self.session = ClientSession()

    async def process_update(self, update: Update):
        if update.message:
            # Validate message length
            if len(update.message.text or '') > MAX_MESSAGE_LENGTH:
                raise Exception("Message too long")
                
            # Validate file size if present
            if update.message.document or update.message.photo:
                file_size = 0
                if update.message.document:
                    file_size = update.message.document.file_size
                elif update.message.photo:
                    file_size = max(p.file_size for p in update.message.photo)
                    
                if file_size > MAX_FILE_SIZE:
                    raise Exception("File too large")

# Initialize message validator
message_validator = MessageValidator()

dp.middleware.setup(message_validator)

# Import handlers from main bot file
from mybot import (
    get_registration_handlers,
    get_login_handlers,
    get_credentials_handlers,
    start,
    watch,
    points,
    confirm,
    balance,
    setwallet,
    mywallet,
    withdraw,
    daily,
    referral,
    tasks,
    logout,
    update_credentials,
    upload,
    stats,
    setdomain
)

# Import TON payment system
from ton_payments import ton_payment
from security_2fa import two_fa

# TON payment commands
async def create_ad(update: types.Update, context: types.ContextTypes.DEFAULT_TYPE):
    """Create new advertisement with TON payment."""
    try:
        user_id = update.message.from_user.id
        
        # Check 2FA status
        if not await two_fa.check_2fa_attempts(user_id):
            await update.message.reply("Too many failed 2FA attempts. Please try again later.")
            return
            
        # Get payment amount from message
        amount = 1.0  # Default amount in TON
        if len(context.args) > 0:
            try:
                amount = float(context.args[0])
            except ValueError:
                await update.message.reply("Invalid amount. Please use a number.")
                return
        
        # Generate 2FA code
        code = await two_fa.generate_2fa_code(user_id)
        
        # Create payment address
        payment = await ton_payment.create_payment_address(user_id, amount)
        
        # Create payment keyboard
        keyboard = await ton_payment.create_payment_keyboard(payment['payment_id'])
        
        # Send payment instructions with 2FA code
        await update.message.reply(
            f"To create an advertisement, please send {amount} TON to:\n\n"
            f"TON Address: {payment['address']}\n\n"
            f"2FA Code: {code}\n\n"
            f"Payment expires in: {PAYMENT_TIMEOUT // 60} minutes\n\n"
            f"After payment confirmation, you can create your advertisement.",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error creating ad payment: {str(e)}")
        await update.message.reply("Error creating advertisement payment. Please try again.")

async def check_payment_callback(update: types.Update, context: types.ContextTypes.DEFAULT_TYPE):
    """Check payment status callback."""
    try:
        query = update.callback_query
        
        # Validate query data
        if not query.data or not query.data.startswith('check_payment_'):
            raise ValueError("Invalid callback data format")
            
        try:
            payment_id = int(query.data.split('_')[2])
        except (ValueError, IndexError):
            raise ValueError("Invalid payment ID in callback data")
        
        # Check payment status
        try:
            payment = await ton_payment.check_payment_status(payment_id)
            if not payment:
                raise ValueError("Payment not found")
                
            # Format payment status message
            status = payment.get('status', 'unknown')
            amount = payment.get('amount', 0)
            address = payment.get('address', '')
            created_at = payment.get('created_at', '')
            expires_at = payment.get('expires_at', '')
            
            # Create keyboard based on payment status
            keyboard = InlineKeyboardMarkup()
            if status == 'pending':
                keyboard.add(
                    InlineKeyboardButton(
                        text="Check Again",
                        callback_data=f"check_payment_{payment_id}"
                    )
                )
            elif status == 'confirmed':
                keyboard.add(
                    InlineKeyboardButton(
                        text="Create Advertisement",
                        callback_data=f"create_ad_{payment_id}"
                    )
                )
            else:
                keyboard.add(
                    InlineKeyboardButton(
                        text="Cancel Payment",
                        callback_data=f"cancel_payment_{payment_id}"
                    )
                )
            
            # Update message with detailed status
            await query.message.edit_text(
                f"Payment Status: {status.upper()}\n\n"
                f"Amount: {amount} TON\n"
                f"Address: {address}\n"
                f"Created: {created_at}\n"
                f"Expires: {expires_at}",
                reply_markup=keyboard
            )
            
            # Handle confirmed payment
            if status == 'confirmed':
                await query.message.edit_reply_markup(
                    InlineKeyboardMarkup().add(
                        InlineKeyboardButton(
                            text="Create Advertisement",
                            callback_data=f"create_ad_{payment_id}"
                        )
                    )
                )
                
                # Set state for ad creation
                context.user_data['payment_id'] = payment_id
                context.user_data['state'] = 'WAITING_FOR_AD_DETAILS'
                
        except Exception as payment_error:
            logger.error(f"Error checking payment status: {str(payment_error)}")
            error_msg = "Error checking payment status. Please try again."
            if isinstance(payment_error, ValueError):
                error_msg = f"Payment error: {str(payment_error)}"
            await query.message.edit_text(error_msg)
            
    except ValueError as e:
        logger.error(f"Invalid callback data: {str(e)}")
        await query.message.edit_text("Invalid payment request. Please try again.")
    except (aiogram.exceptions.NetworkError, aiogram.exceptions.TelegramAPIError) as e:
        logger.error(f"Telegram API error: {str(e)}")
        await query.message.edit_text("Network error. Please try again later.")
    except Exception as e:
        logger.error(f"Unexpected error in payment callback: {str(e)}", exc_info=True)
        await query.message.edit_text("An unexpected error occurred. Please contact support.")

async def show_payment_analytics(update: Update, context: dict):
    """Show payment analytics."""
    try:
        analytics = await ton_payment.get_payment_analytics()
        
        # Format analytics message
        message = f"Payment Analytics:\n\n"
        message += f"Total Payments: {analytics['total_payments']}\n"
        message += f"Successful Payments: {analytics['successful_payments']}\n"
        message += f"Failed Payments: {analytics['failed_payments']}\n\n"
        message += f"Total Amount: {analytics['total_amount']:.2f} TON\n"
        message += f"Average Amount: {analytics['average_amount']:.2f} TON\n\n"
        
        # Add daily stats
        message += "Daily Statistics:\n"
        for date, count in sorted(analytics['daily_stats'].items(), reverse=True):
            message += f"{date}: {count} payments\n"
        
        await update.message.reply(message)
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        await update.message.reply("Error getting payment analytics")

async def show_monitoring_status(update: types.Update, context: types.ContextTypes.DEFAULT_TYPE):
    """Show monitoring status."""
    try:
        # Get current monitoring status
        status = {
            'monitoring_thread': 'Running' if monitoring_thread.is_alive() else 'Stopped',
            'rate_limits': len(rate_limits),
            'failed_attempts': len(failed_attempts),
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Format status message
        message = f"Monitoring Status:\n\n"
        message += f"Monitoring Thread: {status['monitoring_thread']}\n"
        message += f"Active Rate Limits: {status['rate_limits']}\n"
        message += f"Failed Attempts: {status['failed_attempts']}\n"
        message += f"Last Update: {status['last_update']}\n\n"
        
        # Add suspicious activity if any
        suspicious = []
        for user_id, count in rate_limits.items():
            if count > MAX_REQUESTS_PER_MINUTE:
                suspicious.append(f"User {user_id}: {count} requests")
        
        if suspicious:
            message += "Suspicious Activity:\n"
            message += "\n".join(suspicious)
        
        await update.message.reply(message)
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {str(e)}")
        await update.message.reply("Error getting monitoring status")

async def process_ad_details(update: types.Update, context: types.ContextTypes.DEFAULT_TYPE):
    """Process advertisement details after payment confirmation."""
    try:
        if 'payment_id' not in context.user_data:
            await update.message.reply("No active payment found. Please create a new payment first.")
            return
            
        payment_id = context.user_data['payment_id']
        
        # Get ad details from message
        message = update.message
        title = message.text.split('\n')[0]
        description = '\n'.join(message.text.split('\n')[1:])
        media_url = None
        
        # Get media URL if present
        if message.photo:
            media_url = message.photo[-1].file_id
        elif message.document:
            media_url = message.document.file_id
        
        if not media_url:
            await update.message.reply("Please provide a media file (photo or document).")
            return
            
        # Create advertisement
        await ton_payment.create_advertisement(
            message.from_user.id,
            payment_id,
            title,
            description,
            media_url
        )
        
        await update.message.reply("Advertisement created successfully!")
        
    except Exception as e:
        logger.error(f"Error processing ad details: {str(e)}")
        await update.message.reply("Error creating advertisement. Please try again.")
        
    finally:
        # Clear payment context
        if 'payment_id' in context.user_data:
            del context.user_data['payment_id']

# Set up command handlers
async def setup_commands(dp: Dispatcher):
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="register", description="Register new account"),
        BotCommand(command="login", description="Login to your account"),
        BotCommand(command="watch", description="Get videos to watch"),
        BotCommand(command="points", description="Check your points"),
        BotCommand(command="confirm", description="Confirm video watching"),
        BotCommand(command="balance", description="Check your balance"),
        BotCommand(command="setwallet", description="Set TON wallet address"),
        BotCommand(command="mywallet", description="View your wallet"),
        BotCommand(command="withdraw", description="Withdraw TON"),
        BotCommand(command="daily", description="Claim daily bonus"),
        BotCommand(command="referral", description="Get referral link"),
        BotCommand(command="tasks", description="View your tasks"),
        BotCommand(command="logout", description="Logout from account"),
        BotCommand(command="update_credentials", description="Update GPT credentials"),
        BotCommand(command="upload", description="Upload video (admin only)"),
        BotCommand(command="stats", description="View bot statistics (admin only)"),
        BotCommand(command="setdomain", description="Set domain (admin only)")
    ]
    await bot.set_my_commands(commands)

async def setup_2fa(update: types.Update, context: types.ContextTypes.DEFAULT_TYPE):
    """Setup 2FA for user."""
    try:
        user_id = update.message.from_user.id
        
        # Check if method is provided
        if len(context.args) == 0:
            # Show method selection keyboard
            keyboard = await two_fa.create_2fa_keyboard(user_id)
            await update.message.reply(
                "Select your preferred 2FA method:",
                reply_markup=keyboard
            )
            return
            
        method = context.args[0].lower()
        if method not in TWO_FA_METHODS:
            await update.message.reply(
                "Invalid 2FA method. Available methods: " + ", ".join(TWO_FA_METHODS)
            )
            return
            
        # Setup 2FA
        if await two_fa.setup_2fa(user_id, method):
            await update.message.reply(
                f"2FA setup complete!\n\n"
                f"Please check your {method} for setup instructions."
            )
        else:
            await update.message.reply("Error setting up 2FA")
            
    except Exception as e:
        logger.error(f"Error setting up 2FA: {str(e)}")
        await update.message.reply("Error setting up 2FA. Please try again.")

async def check_2fa(update: types.Update, context: types.ContextTypes.DEFAULT_TYPE):
    """Check 2FA status."""
    try:
        user_id = update.message.from_user.id
        
        # Generate new code
        code = await two_fa.generate_2fa_code(user_id)
        
        await update.message.reply(
            f"Your 2FA code: {code}\n\n"
            "This code will expire in 5 minutes."
        )
        
    except Exception as e:
        logger.error(f"Error checking 2FA: {str(e)}")
        await update.message.reply("Error checking 2FA status. Please try again.")

async def main():
    # Initialize bot and dispatcher
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    dp = Dispatcher()
    
    # Set up webhook
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        await bot.set_webhook(webhook_url)
    else:
        logger.info("Starting bot in polling mode")
        
    try:
        # Register commands
        commands = [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="watch", description="Watch video"),
            BotCommand(command="points", description="Check points"),
            BotCommand(command="balance", description="Check balance"),
            BotCommand(command="daily", description="Claim daily bonus"),
            BotCommand(command="stats", description="Show statistics"),
            BotCommand(command="logout", description="Logout"),
            BotCommand(command="createad", description="Create advertisement with TON payment"),
            BotCommand(command="payments", description="Show payment analytics"),
            BotCommand(command="monitor", description="Show monitoring status"),
            BotCommand(command="setup2fa", description="Setup 2FA for payments"),
            BotCommand(command="check2fa", description="Check 2FA status")
        ]
        await bot.set_my_commands(commands)
        
        # Register security middleware
        dp.middleware.setup(security_middleware)
        
        # Add handlers
        dp.message.register(create_ad, Command('createad'))
        dp.callback_query.register(check_payment_callback, Text(startswith="check_payment_"))
        dp.message.register(process_ad_details, Command('payments'))
        dp.message.register(show_payment_analytics, Command('payments'))
        dp.message.register(show_monitoring_status, Command('monitor'))
        dp.message.register(setup_2fa, Command('setup2fa'))
        dp.message.register(check_2fa, Command('check2fa'))
        
        # Start the bot
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Bot startup error: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)
