import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from typing import Dict, Any, Optional
import sqlite3
import logging
import os
import time
from security_checks import SecurityChecks
from registration_constants import RegistrationStates, RegistrationMessages
from registration_analytics import RegistrationAnalytics
from registration_validation import RegistrationValidator
from registration_helpers import RegistrationHelper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize managers
security = SecurityChecks(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'botdata.db'))
analytics = RegistrationAnalytics(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'botdata.db'))
validator = RegistrationValidator()
helper = RegistrationHelper()

# Rate limiting
RATE_LIMIT = 5  # max attempts per hour
RATE_LIMIT_PERIOD = 3600  # 1 hour in seconds

# Database connection
def get_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'botdata.db')
    return sqlite3.connect(db_path)

def get_user_attempts(user_id: int) -> int:
    """Get number of registration attempts in the last hour."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT COUNT(*) 
            FROM registration_attempts 
            WHERE user_id = ? 
            AND attempt_timestamp >= datetime('now', ?)
        ''', (user_id, f'-{RATE_LIMIT_PERIOD} seconds'))
        return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logger.error(f"Error getting attempts: {str(e)}")
        return 0
    finally:
        conn.close()

def log_attempt(user_id: int, step: str, error_type: str, error_message: str):
    """Log a registration attempt."""
    analytics.log_attempt(user_id, step, error_type, error_message)
    validator.log_validation_attempt(user_id, step, {'error': error_message}, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'botdata.db'))
    helper.log_attempt(user_id, step, error_type, error_message)

def log_event(user_id: int, event_type: str, event_data: Dict[str, Any], status: str = 'success'):
    """Log a registration event."""
    analytics.log_event(user_id, event_type, event_data, status)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler."""
    # Check rate limit
    attempts = get_user_attempts(update.effective_user.id)
    if attempts >= RATE_LIMIT:
        log_attempt(
            update.effective_user.id,
            "start",
            "rate_limit",
            "Exceeded maximum attempts"
        )
        await update.message.reply_text(
            RegistrationMessages.ERROR_RATE_LIMIT
        )
        return ConversationHandler.END

    # Check if user is already registered
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, agreement_accepted FROM users WHERE telegram_id = ?', (update.effective_user.id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        if user[1]:  # agreement_accepted
            await update.message.reply_text("You are already registered!")
            return ConversationHandler.END
        else:
            # Show agreement again
            keyboard = ReplyKeyboardMarkup(
                RegistrationMessages.KEYBOARD[0],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            
            await update.message.reply_text(
                RegistrationMessages.WELCOME + "\n\n" + RegistrationMessages.TERMS_OF_SERVICE,
                reply_markup=keyboard
            )
            return RegistrationStates.AGREEMENT

    # Show agreement
    keyboard = ReplyKeyboardMarkup(
        RegistrationMessages.KEYBOARD[0],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        RegistrationMessages.WELCOME + "\n\n" + RegistrationMessages.TERMS_OF_SERVICE,
        reply_markup=keyboard
    )
    
    # Log start event
    log_event(
        update.effective_user.id,
        "registration_start",
        {
            "user_id": update.effective_user.id,
            "username": update.effective_user.username,
            "timestamp": datetime.now().isoformat()
        }
    )
    
    return RegistrationStates.AGREEMENT

async def agreement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle agreement response."""
    if update.message.text.lower() != "accept":
        log_attempt(
            update.effective_user.id,
            "agreement",
            "invalid_response",
            "User declined agreement"
        )
        await update.message.reply_text(
            RegistrationMessages.ERROR_INVALID_INPUT,
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # Check if user exists but needs agreement
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (update.effective_user.id,))
    user = cursor.fetchone()
    
    if user:
        # Update agreement status
        cursor.execute('UPDATE users SET agreement_accepted = 1 WHERE id = ?', (user[0],))
        conn.commit()
        await update.message.reply_text(
            RegistrationMessages.SUCCESS,
            reply_markup=ReplyKeyboardRemove()
        )
        conn.close()
        return ConversationHandler.END

    # Log agreement acceptance
    log_event(
        update.effective_user.id,
        "agreement_accepted",
        {
            "user_id": update.effective_user.id,
            "timestamp": datetime.now().isoformat()
        }
    )

    # Ask for username
    await update.message.reply_text(
        RegistrationMessages.USERNAME_PROMPT + "\n\n" + validator.get_validation_report({'username': ''}),
        reply_markup=ReplyKeyboardRemove()
    )
    return RegistrationStates.USERNAME

async def username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle username input."""
    username = update.message.text.strip()
    
    # Get remaining attempts
    remaining_attempts = helper.get_remaining_attempts(update.effective_user.id, 'username')
    if remaining_attempts <= 0:
        time_remaining = helper.get_time_remaining(update.effective_user.id, 'username')
        if time_remaining:
            minutes = int(time_remaining.total_seconds() // 60)
            seconds = int(time_remaining.total_seconds() % 60)
            await update.message.reply_text(
                f"❌ Too many attempts. Please wait {minutes} minutes and {seconds} seconds before trying again."
            )
            return RegistrationStates.USERNAME

    # Validate username
    result = validator.validate_username(username)
    if not result['valid']:
        log_attempt(
            update.effective_user.id,
            "username",
            "validation_error",
            result['error']
        )
        await update.message.reply_text(
            helper.format_error_message(
                "validation_error",
                result['error'],
                'username'
            )
        )
        return RegistrationStates.USERNAME

    # Check username uniqueness
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE username = ?', (username,))
    if cursor.fetchone():
        log_attempt(
            update.effective_user.id,
            "username",
            "exists",
            "Username already exists"
        )
        await update.message.reply_text(
            helper.format_error_message(
                "exists",
                "Username already exists",
                'username'
            )
        )
        conn.close()
        return RegistrationStates.USERNAME
    conn.close()

    # Log username selection
    log_event(
        update.effective_user.id,
        "username_selected",
        {
            "username": username,
            "timestamp": datetime.now().isoformat()
        }
    )

    # Store username in context
    context.user_data['username'] = username

    # Show progress and ask for password
    await update.message.reply_text(
        f"{helper.get_progress_message(context.user_data)}\n\n" +
        RegistrationMessages.PASSWORD_PROMPT + "\n\n" +
        helper.format_validation_report({'password': True})
    )
    return RegistrationStates.PASSWORD

async def password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle password input."""
    password = update.message.text.strip()
    
    # Get remaining attempts
    remaining_attempts = helper.get_remaining_attempts(update.effective_user.id, 'password')
    if remaining_attempts <= 0:
        time_remaining = helper.get_time_remaining(update.effective_user.id, 'password')
        if time_remaining:
            minutes = int(time_remaining.total_seconds() // 60)
            seconds = int(time_remaining.total_seconds() % 60)
            await update.message.reply_text(
                f"❌ Too many attempts. Please wait {minutes} minutes and {seconds} seconds before trying again."
            )
            return RegistrationStates.PASSWORD

    # Validate password
    result = validator.validate_password(password)
    if not result['valid']:
        log_attempt(
            update.effective_user.id,
            "password",
            "validation_error",
            result['error']
        )
        await update.message.reply_text(
            helper.format_error_message(
                "validation_error",
                result['error'],
                'password'
            )
        )
        return RegistrationStates.PASSWORD

    # Log password validation
    log_event(
        update.effective_user.id,
        "password_validated",
        {
            "length": len(password),
            "timestamp": datetime.now().isoformat()
        }
    )

    # Store password in context
    context.user_data['password'] = password

    # Show progress and ask for GPT credentials
    await update.message.reply_text(
        f"{helper.get_progress_message(context.user_data)}\n\n" +
        RegistrationMessages.GPT_PROMPT + "\n\n" +
        helper.format_validation_report({'gpt_username': True, 'gpt_password': True})
    )
    return RegistrationStates.GPT_CREDENTIALS

async def gpt_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle GPT credentials input."""
    credentials = update.message.text.strip().split('|')
    
    # Get remaining attempts
    remaining_attempts = helper.get_remaining_attempts(update.effective_user.id, 'gpt_credentials')
    if remaining_attempts <= 0:
        time_remaining = helper.get_time_remaining(update.effective_user.id, 'gpt_credentials')
        if time_remaining:
            minutes = int(time_remaining.total_seconds() // 60)
            seconds = int(time_remaining.total_seconds() % 60)
            await update.message.reply_text(
                f"❌ Too many attempts. Please wait {minutes} minutes and {seconds} seconds before trying again."
            )
            return RegistrationStates.GPT_CREDENTIALS

    if len(credentials) != 2:
        log_attempt(
            update.effective_user.id,
            "gpt_credentials",
            "invalid_format",
            "Credentials not in username|password format"
        )
        await update.message.reply_text(
            helper.format_error_message(
                "invalid_format",
                "Credentials must be in format: username|password",
                'gpt_credentials'
            )
        )
        return RegistrationStates.GPT_CREDENTIALS

    gpt_username, gpt_password = credentials
    
    # Validate GPT credentials
    result = validator.validate_gpt_credentials(gpt_username, gpt_password)
    if not result['valid']:
        log_attempt(
            update.effective_user.id,
            "gpt_credentials",
            "validation_error",
            result['error']
        )
        await update.message.reply_text(
            helper.format_error_message(
                "validation_error",
                result['error'],
                'gpt_credentials'
            )
        )
        return RegistrationStates.GPT_CREDENTIALS

    # Log GPT credentials validation
    log_event(
        update.effective_user.id,
        "gpt_credentials_validated",
        {
            "username_length": len(gpt_username),
            "password_length": len(gpt_password),
            "timestamp": datetime.now().isoformat()
        }
    )

    # Store credentials in context
    context.user_data['gpt_username'] = gpt_username
    context.user_data['gpt_password'] = gpt_password

    # Show progress and confirmation
    keyboard = ReplyKeyboardMarkup(
        RegistrationMessages.KEYBOARD[1],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        f"{helper.get_progress_message(context.user_data)}\n\n" +
        RegistrationMessages.get_confirmation_message(context.user_data),
        reply_markup=keyboard
    )
    return RegistrationStates.CONFIRMATION

    # Save to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (telegram_id, username, password, 
                             gpt_username, gpt_password, points, 
                             agreement_accepted, registration_date)
            VALUES (?, ?, ?, ?, ?, 0, 1, CURRENT_TIMESTAMP)
        ''', (
            update.effective_user.id,
            context.user_data['username'],
            context.user_data['password'],
            context.user_data['gpt_username'],
            context.user_data['gpt_password']
        ))
        conn.commit()
        
        await update.message.reply_text(
            "Registration completed successfully!\n\n"
            "You can now use all bot commands."
        )
    except sqlite3.Error as e:
        logger.error(f"Error registering user: {str(e)}")
        security.log_failed_attempt(update.effective_user.id, 'registration', str(e))
        await update.message.reply_text(
            "Error registering user. Please try again."
        )
    finally:
        conn.close()

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the registration process."""
    await update.message.reply_text(
        "Registration cancelled. You can start over by typing /start",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle registration confirmation."""
    start_time = time.time()
    
    # Get remaining attempts
    remaining_attempts = helper.get_remaining_attempts(update.effective_user.id, 'confirmation')
    if remaining_attempts <= 0:
        time_remaining = helper.get_time_remaining(update.effective_user.id, 'confirmation')
        if time_remaining:
            minutes = int(time_remaining.total_seconds() // 60)
            seconds = int(time_remaining.total_seconds() % 60)
            await update.message.reply_text(
                f"❌ Too many attempts. Please wait {minutes} minutes and {seconds} seconds before trying again."
            )
            return RegistrationStates.CONFIRMATION

    if update.message.text.lower() != "confirm":
        log_attempt(
            update.effective_user.id,
            "confirmation",
            "invalid_response",
            "User did not confirm registration"
        )
        await update.message.reply_text(
            RegistrationMessages.ERROR_INVALID_INPUT,
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # Validate complete registration data
    result = validator.validate_registration(context.user_data)
    if not result['valid']:
        log_attempt(
            update.effective_user.id,
            "confirmation",
            "validation_error",
            str(result['errors'])
        )
        await update.message.reply_text(
            "❌ Validation failed:\n" + 
            "\n".join(f"- {error}" for error in result['errors'].values()) +
            "\n\n" + helper.get_validation_report(context.user_data)
        )
        return RegistrationStates.START

    # Save to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (telegram_id, username, password, 
                             gpt_username, gpt_password, points, 
                             agreement_accepted, registration_date)
            VALUES (?, ?, ?, ?, ?, 0, 1, CURRENT_TIMESTAMP)
        ''', (
            update.effective_user.id,
            context.user_data['username'],
            context.user_data['password'],
            context.user_data['gpt_username'],
            context.user_data['gpt_password']
        ))
        conn.commit()
        
        # Log successful registration
        duration = int(time.time() - start_time)
        log_event(
            update.effective_user.id,
            "registration_completed",
            {
                "username": context.user_data['username'],
                "gpt_username": context.user_data['gpt_username'],
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        await update.message.reply_text(
            RegistrationMessages.SUCCESS,
            reply_markup=ReplyKeyboardRemove()
        )
    except sqlite3.Error as e:
        logger.error(f"Error registering user: {str(e)}")
        security.log_failed_attempt(update.effective_user.id, 'registration', str(e))
        log_attempt(
            update.effective_user.id,
            "registration",
            "database_error",
            str(e)
        )
        await update.message.reply_text(
            RegistrationMessages.ERROR_SYSTEM
        )
    finally:
        conn.close()

    return ConversationHandler.END

def get_registration_handlers() -> ConversationHandler:
    """Get registration command handlers."""
    return ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            RegistrationStates.AGREEMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, agreement)
            ],
            RegistrationStates.USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, username)
            ],
            RegistrationStates.PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, password)
            ],
            RegistrationStates.GPT_CREDENTIALS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_credentials)
            ],
            RegistrationStates.CONFIRMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start)
        ],
        allow_reentry=False
    )
