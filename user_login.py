import sqlite3
import os
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

# Define conversation states
USERNAME, PASSWORD = range(2)

# Database connection
def get_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'botdata.db')
    return sqlite3.connect(db_path)

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the login process."""
    user_id = update.effective_user.id
    
    # Check if user is already logged in
    if context.user_data.get('logged_in', False):
        await update.message.reply_text("You are already logged in!")
        return ConversationHandler.END
    
    await update.message.reply_text("Please enter your username:")
    return USERNAME

async def process_login_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the username input."""
    username = update.message.text.strip()
    
    # Check if username exists in the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        await update.message.reply_text("Username not found.\n"
                                     "Would you like to register?\n"
                                     "Send /register to start registration.")
        return ConversationHandler.END
    
    # Store username temporarily
    context.user_data['login_username'] = username
    await update.message.reply_text("Please enter your password:")
    return PASSWORD

async def process_login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the password input."""
    password = update.message.text
    
    # Get stored username
    username = context.user_data.get('login_username')
    if not username:
        await update.message.reply_text("Login process interrupted. Please start again.")
        return ConversationHandler.END
    
    # Verify credentials
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        # Mark user as logged in
        context.user_data['logged_in'] = True
        context.user_data['user_id'] = user[0]  # Store user ID
        
        await update.message.reply_text("Login successful!\n"
                                     "You can now use the bot features.")
    else:
        await update.message.reply_text("Incorrect password.\n"
                                     "Would you like to try again? Send /login")
    
    return ConversationHandler.END

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logout the user."""
    if context.user_data.get('logged_in', False):
        context.user_data['logged_in'] = False
        context.user_data.pop('user_id', None)
        context.user_data.pop('login_username', None)
        await update.message.reply_text("You have been logged out.")
    else:
        await update.message.reply_text("You are not logged in.")
    return ConversationHandler.END

def get_login_handlers():
    """Return the login conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler('login', login)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_login_username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_login_password)],
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)]
    )
