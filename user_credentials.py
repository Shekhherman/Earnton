import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from gpt_platform import GPTPlatform
import re
import random

# Password strength levels
WEAK = 1
MEDIUM = 2
STRONG = 3

# Password requirements
MIN_LENGTH = 8
REQUIREMENTS = [
    r'[A-Z]',     # Uppercase
    r'[a-z]',     # Lowercase
    r'[0-9]',     # Numbers
    r'[!@#$%^&*(),.?":{}|<>]'  # Special characters
]

# Define conversation states
CURRENT_PASSWORD, GPT_USERNAME, GPT_PASSWORD, CONFIRM_UPDATE = range(4)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'botdata.db')
    return sqlite3.connect(db_path)

async def update_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the credentials update process."""
    if not context.user_data.get('logged_in', False):
        await update.message.reply_text("Please login first using /login")
        return ConversationHandler.END
    
    await update.message.reply_text("Please enter your current password to verify your identity:")
    return CURRENT_PASSWORD

async def process_current_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify current password."""
    current_password = update.message.text
    
    # Verify current password
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ? AND password = ?', 
                  (context.user_data['user_id'], current_password))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        await update.message.reply_text("Incorrect current password.\n"
                                     "Would you like to try again? Send /update_credentials")
        return ConversationHandler.END
    
    await update.message.reply_text("Please enter your new GPT username:")
    return GPT_USERNAME

async def process_new_gpt_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the new GPT username input."""
    gpt_username = update.message.text.strip()
    
    # Username validation
    if not gpt_username:
        await update.message.reply_text("GPT username cannot be empty.\n"
                                     "Please try again:")
        return GPT_USERNAME
    
    if len(gpt_username) > 50:
        await update.message.reply_text("Username is too long (max 50 characters).\n"
                                     "Please try again:")
        return GPT_USERNAME
    
    if not re.match(r'^[a-zA-Z0-9_]+$', gpt_username):
        await update.message.reply_text("Username can only contain letters, numbers, and underscores.\n"
                                     "Please try again:")
        return GPT_USERNAME
    
    # Validate username with GPT platform
    gpt = GPTPlatform()
    if not await gpt.validate_credentials(gpt_username, context.user_data.get('gpt_password')):
        await update.message.reply_text("This GPT username is not valid or doesn't exist.\n"
                                     "Please check your credentials and try again.")
        return GPT_USERNAME
    
    context.user_data['new_gpt_username'] = gpt_username
    
    # Generate password strength suggestions
    suggestions = generate_password_suggestions()
    
    await update.message.reply_text(
        "Please enter your new GPT password:\n\n"
        f"Password must be at least {MIN_LENGTH} characters long\n"
        "Must contain at least one uppercase letter\n"
        "Must contain at least one number\n"
        "Must contain at least one special character\n\n"
        "Here are some suggestions:\n"
        f"{suggestions[0]}\n"
        f"{suggestions[1]}\n"
        f"{suggestions[2]}"
    )
    return GPT_PASSWORD

async def process_new_gpt_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the new GPT password input and check strength."""
    gpt_password = update.message.text
    
    # Check password strength
    strength = check_password_strength(gpt_password)
    
    if strength == WEAK:
        await update.message.reply_text("Password is too weak.\n"
                                     "It must contain at least:\n"
                                     "- 8 characters\n"
                                     "- One uppercase letter\n"
                                     "- One lowercase letter\n"
                                     "- One number\n"
                                     "- One special character\n"
                                     "Please try again:")
        return GPT_PASSWORD
    
    if strength == MEDIUM:
        await update.message.reply_text("Password is medium strength.\n"
                                     "Adding more special characters or numbers would make it stronger.\n"
                                     "Would you like to try a stronger password?\n"
                                     "Send /cancel to proceed with this password")
        return GPT_PASSWORD
    
    # Validate with GPT platform
    gpt = GPTPlatform()
    if not await gpt.validate_credentials(context.user_data['new_gpt_username'], gpt_password):
        await update.message.reply_text("These GPT credentials are not valid.\n"
                                     "Please check your credentials and try again.")
        return GPT_PASSWORD
    
    # Get user data
    user_data = await gpt.get_user_data(context.user_data['new_gpt_username'], gpt_password)
    if user_data:
        balance = user_data.get('balance', 0)
        status = user_data.get('status', 'Unknown')
        
        # Store additional user data
        context.user_data['gpt_balance'] = balance
        context.user_data['gpt_status'] = status
    
    context.user_data['new_gpt_password'] = gpt_password
    
    # Confirmation step
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Yes"), KeyboardButton("No")]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    
    await update.message.reply_text(
        "Your credentials will be updated with:\n"
        f"GPT Username: {context.user_data['new_gpt_username']}\n"
        f"GPT Balance: {context.user_data.get('gpt_balance', 'Unknown')}\n"
        f"GPT Status: {context.user_data.get('gpt_status', 'Unknown')}\n"
        "Are you sure you want to proceed?",
        reply_markup=keyboard
    )
    return CONFIRM_UPDATE

async def process_confirm_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the update confirmation."""
    if update.message.text.lower() == 'yes':
        user_id = context.user_data.get('user_id')
        if not user_id:
            await update.message.reply_text("Session expired. Please login again using /login")
            return ConversationHandler.END
        
        # Update credentials in database
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE users 
                SET gpt_username = ?, gpt_password = ?
                WHERE user_id = ?
            ''', (context.user_data['new_gpt_username'], 
                  context.user_data['new_gpt_password'], 
                  user_id))
            conn.commit()
            
            await update.message.reply_text("Credentials updated successfully!")
        except Exception as e:
            await update.message.reply_text(f"Failed to update credentials: {str(e)}")
        finally:
            conn.close()
    else:
        await update.message.reply_text("Credentials update cancelled.")
    
    return ConversationHandler.END

async def cancel_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the credentials update process."""
    await update.message.reply_text("Credentials update cancelled.")
    return ConversationHandler.END

# Helper functions
def check_password_strength(password: str) -> int:
    """Check password strength and return level."""
    strength = 0
    
    # Check length
    if len(password) >= MIN_LENGTH:
        strength += 1
    
    # Check requirements
    for req in REQUIREMENTS:
        if re.search(req, password):
            strength += 1
    
    if strength < 3:
        return WEAK
    elif strength < 5:
        return MEDIUM
    return STRONG

def generate_password_suggestions() -> list:
    """Generate random password suggestions."""
    suggestions = []
    for _ in range(3):
        password = ''.join(random.choices(
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()',
            k=random.randint(12, 16)
        ))
        suggestions.append(password)
    return suggestions

def get_credentials_handlers():
    """Return the credentials update conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler('update_credentials', update_credentials)],
        states={
            CURRENT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_current_password)],
            GPT_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_new_gpt_username)],
            GPT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_new_gpt_password)],
            CONFIRM_UPDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_confirm_update)],
        },
        fallbacks=[CommandHandler('cancel', cancel_credentials)]
    )
