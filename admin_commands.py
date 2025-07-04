import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from typing import Optional, Dict, Any
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin commands
UPLOAD, STATS, SETDOMAIN = range(3)

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video upload command."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is only available to admins.")
        return

    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("Cancel")]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "Please enter the video details:\n\n"
        "Format: title|url|category_id|points\n\n"
        "Example: Python Tutorial|https://example.com/video|1|10",
        reply_markup=keyboard
    )
    return UPLOAD

async def process_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process video upload details."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is only available to admins.")
        return ConversationHandler.END

    video_data = update.message.text.split('|')
    if len(video_data) != 4:
        await update.message.reply_text(
            "Invalid format!\n"
            "Please use: title|url|category_id|points"
        )
        return UPLOAD

    title, url, category_id, points = video_data
    
    try:
        category_id = int(category_id)
        points = int(points)
    except ValueError:
        await update.message.reply_text(
            "Category ID and points must be numbers!"
        )
        return UPLOAD

    # Save to database
    conn = sqlite3.connect('botdata.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO videos (title, url, category_id, points, uploader_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, url, category_id, points, update.effective_user.id))
        conn.commit()
        
        await update.message.reply_text(
            f"Video '{title}' uploaded successfully!"
        )
    except sqlite3.Error as e:
        logger.error(f"Error uploading video: {str(e)}")
        await update.message.reply_text(
            "Error uploading video. Please check the details and try again."
        )
    finally:
        conn.close()

    return ConversationHandler.END

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is only available to admins.")
        return

    conn = sqlite3.connect('botdata.db')
    cursor = conn.cursor()
    
    try:
        # Get user stats
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        total_admins = cursor.fetchone()[0]
        
        # Get video stats
        cursor.execute('SELECT COUNT(*) FROM videos')
        total_videos = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM video_watches 
            WHERE watch_date >= date('now', '-7 days')
        ''')
        weekly_watches = cursor.fetchone()[0]
        
        # Get points stats
        cursor.execute('SELECT SUM(points) FROM users')
        total_points = cursor.fetchone()[0] or 0
        
        # Format stats
        stats_text = (
            "📊 Bot Statistics\n\n"
            f"👥 Users: {total_users}\n"
            f"👑 Admins: {total_admins}\n\n"
            f"🎥 Videos: {total_videos}\n"
            f"👁️ Weekly Watches: {weekly_watches}\n\n"
            f"⭐ Total Points: {total_points}\n"
        )
        
        await update.message.reply_text(stats_text)
    except sqlite3.Error as e:
        logger.error(f"Error getting stats: {str(e)}")
        await update.message.reply_text("Error getting statistics.")
    finally:
        conn.close()

async def setdomain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the domain for video redirects."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is only available to admins.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a domain name.")
        return

    domain = context.args[0]
    
    # Save to database
    conn = sqlite3.connect('botdata.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        ''', ('redirect_domain', domain))
        conn.commit()
        
        await update.message.reply_text(
            f"Domain set to: {domain}"
        )
    except sqlite3.Error as e:
        logger.error(f"Error setting domain: {str(e)}")
        await update.message.reply_text(
            "Error setting domain. Please check the format and try again."
        )
    finally:
        conn.close()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation."""
    await update.message.reply_text(
        "Operation cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    admin_id = os.getenv('ADMIN_ID')
    if not admin_id:
        return False
    return str(user_id) == admin_id

def get_admin_handlers() -> ConversationHandler:
    """Get admin command handlers."""
    return ConversationHandler(
        entry_points=[
            CommandHandler('upload', upload),
            CommandHandler('stats', stats),
            CommandHandler('setdomain', setdomain)
        ],
        states={
            UPLOAD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_upload),
                CommandHandler('cancel', cancel)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
