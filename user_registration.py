import sqlite3
import os
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

# Define conversation states
USERNAME, PASSWORD, GPT_USERNAME, GPT_PASSWORD = range(4)

# Database connection
def get_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'botdata.db')
    return sqlite3.connect(db_path)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the registration process."""
    user_id = update.effective_user.id
    
    # Check if user is already registered
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (user_id,))
    if cursor.fetchone():
        await update.message.reply_text("You are already registered!")
        conn.close()
        return ConversationHandler.END
    
    await update.message.reply_text("Welcome to the registration process!\n"
                                   "Please enter your desired username:")
    conn.close()
    return USERNAME

async def process_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the username input."""
    username = update.message.text.strip()
    
    # Validate username
    if not username.isalnum():
        await update.message.reply_text("Username must contain only letters and numbers.\n"
                                     "Please try again:")
        return USERNAME
    
    # Store username temporarily
    context.user_data['username'] = username
    
    await update.message.reply_text("Please enter your password:")
    return PASSWORD

async def process_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the password input."""
    password = update.message.text
    
    # Validate password
    if len(password) < 6:
        await update.message.reply_text("Password must be at least 6 characters long.\n"
                                     "Please try again:")
        return PASSWORD
    
    context.user_data['password'] = password
    
    await update.message.reply_text("Please enter your GPT username:")
    return GPT_USERNAME

async def process_gpt_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the GPT username input."""
    gpt_username = update.message.text
    
    if not gpt_username:
        await update.message.reply_text("GPT username cannot be empty.\n"
                                     "Please try again:")
        return GPT_USERNAME
    
    context.user_data['gpt_username'] = gpt_username
    
    await update.message.reply_text("Please enter your GPT password:")
    return GPT_PASSWORD

async def process_gpt_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the GPT password input and complete registration."""
    gpt_password = update.message.text
    
    if len(gpt_password) < 6:
        await update.message.reply_text("GPT password must be at least 6 characters long.\n"
                                     "Please try again:")
        return GPT_PASSWORD
    
    # Get all registration data
    user_id = update.effective_user.id
    username = context.user_data['username']
    password = context.user_data['password']
    gpt_username = context.user_data['gpt_username']
    gpt_password = gpt_password
    
    # Store in database
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (telegram_id, username, password, gpt_username, gpt_password)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, password, gpt_username, gpt_password))
        conn.commit()
        
        await update.message.reply_text("Registration completed successfully!\n"
                                     "You can now use the bot features.")
    except sqlite3.IntegrityError:
        await update.message.reply_text("Registration failed. Username already exists.")
    finally:
        conn.close()
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the registration process."""
    await update.message.reply_text("Registration cancelled.")
    return ConversationHandler.END

def get_registration_handlers():
    """Return the registration conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_password)],
            GPT_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_gpt_username)],
            GPT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_gpt_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
