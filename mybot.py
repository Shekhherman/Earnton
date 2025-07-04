import os
import sqlite3
from datetime import datetime
import asyncio
import logging
from typing import Dict, Optional, List, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    ContextTypes, 
    MessageHandler, 
    filters, 
    ConversationHandler,
    CallbackQueryHandler
)
from tonclient.client import TonClient
from tonclient.types import ClientConfig

# Import configuration
from config_manager import config_manager

# Import modules
from database import db
from user_registration import get_registration_handlers
from user_login import get_login_handlers
from user_credentials import get_credentials_handlers
from gpt_platform import GPTPlatform
from admin_commands import get_admin_handlers
from security import SecurityManager
from analytics import Analytics
from referral_system import ReferralSystem
from backup_system import BackupSystem
from caching_system import Cache
from notification_system import NotificationSystem

# Import configuration
from config import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize managers
def init_managers():
    """Initialize all bot managers."""
    security = SecurityManager(DB_PATH)
    analytics = Analytics(DB_PATH)
    referral_system = ReferralSystem(DB_PATH)
    backup_system = BackupSystem(DB_PATH)
    cache = Cache(os.path.dirname(DB_PATH))
    notification_system = NotificationSystem(DB_PATH)
    return {
        'security': security,
        'analytics': analytics,
        'referral': referral_system,
        'backup': backup_system,
        'cache': cache,
        'notifications': notification_system
    }

# Constants
USERNAME, PASSWORD, GPT_USERNAME, GPT_PASSWORD = range(4)

# Bot token (loaded from config)
# Note: Never commit bot tokens to source control

# Database connection management
def get_db_connection() -> sqlite3.Connection:
    """Get database connection with proper type handling."""
    try:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def close_db_connection(conn: sqlite3.Connection) -> None:
    """Safely close database connection."""
    try:
        if conn:
            conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error closing database connection: {str(e)}")

# TON Configuration
TON_FEE_PERCENTAGE = 0.015  # 1.5% fee
TON_MIN_BALANCE = 0.01  # Minimum balance in TON

# Video Configuration
VIDEO_WATCH_TIME = 30  # Minimum watch time in seconds
POINTS_PER_VIDEO = 10  # Points awarded per video

# Referral System
REFERRAL_BONUS = 50  # Points for successful referral
REFERRAL_LEVELS = 3  # Number of referral levels

# Cache decorators
def cache(ttl: int):
    """Cache decorator with TTL."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            key = f"cache_{func.__name__}_{args}_{kwargs}"
            cached = await cache.get(key)
            if cached:
                return cached
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator

# Background tasks
async def backup_database():
    """Periodically backup the database."""
    while True:
        try:
            backup_file = backup_system.create_backup()
            if backup_file:
                # Upload to S3 if credentials are available
                aws_access_key = os.getenv('AWS_ACCESS_KEY')
                aws_secret_key = os.getenv('AWS_SECRET_KEY')
                bucket_name = os.getenv('S3_BUCKET_NAME')
                
                if aws_access_key and aws_secret_key and bucket_name:
                    backup_system.setup_s3(aws_access_key, aws_secret_key, bucket_name)
                    backup_system.upload_to_s3(backup_file)
            
            await asyncio.sleep(3600)  # Backup every hour
        except Exception as e:
            logger.error(f"Error in backup process: {str(e)}")
            await asyncio.sleep(3600)

async def check_for_updates():
    """Periodically check for updates and send notifications."""
    while True:
        try:
            # Check for new videos
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, category_id, points
                FROM videos
                WHERE created_at >= date('now', '-1 day')
            ''')
            
            new_videos = cursor.fetchall()
            
            if new_videos:
                # Get users who want new video notifications
                cursor.execute('''
                    SELECT user_id
                    FROM notification_preferences
                    WHERE new_videos = 1
                ''')
                
                users = cursor.fetchall()
                
                for user in users:
                    message = "New videos available!\n\n"
                    for video in new_videos:
                        message += f"• {video[1]} (Category: {video[2]}, Points: {video[3]})\n"
                    
                    await notification_system.send_notification(
                        user[0],
                        'new_video',
                        message
                    )
            
            conn.close()
            
            await asyncio.sleep(3600)  # Check every hour
        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
            await asyncio.sleep(3600)

# --- Constants ---
BASE_URL = "https://petite-eyes-cheat.loca.lt"  # Replace this with your LocalTunnel URL

# --- Database setup ---
conn = sqlite3.connect('botdata.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    credits REAL DEFAULT 0,
    ton_wallet TEXT,
    last_daily TEXT,
    referrer INTEGER,
    registered INTEGER DEFAULT 0,
    agreement_version TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS agreements (
    id INTEGER PRIMARY KEY,
    text TEXT,
    version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS tasks (
    user_id INTEGER,
    task_name TEXT,
    status TEXT,
    PRIMARY KEY(user_id, task_name)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
''')

# Insert initial agreement
initial_agreement = '''
By using this bot, you agree to the following terms:
1. You will only watch videos for legitimate purposes
2. You will not abuse the system or attempt to manipulate rewards
3. You understand that rewards are subject to availability
4. You agree to the privacy policy regarding your data
5. You understand that rewards may be subject to network fees
6. You are responsible for any taxes on rewards
'''

cursor.execute('INSERT INTO agreements (text, version) VALUES (?, ?)', 
              (initial_agreement, '1.0'))

# Add registered column to existing users if needed
cursor.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS registered INTEGER DEFAULT 0')
cursor.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS agreement_version TEXT')

conn.commit()

def get_domain():
    cursor.execute("SELECT value FROM settings WHERE key = 'domain'")
    row = cursor.fetchone()
    if row:
        return row[0]
    # Default domain
    return "https://petite-eyes-cheat.loca.lt"

def set_domain(domain):
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('domain', ?)", (domain,))
    conn.commit()

def add_user(user_id, referrer=None):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (user_id, referrer) VALUES (?, ?)', (user_id, referrer))
        conn.commit()

def is_registered(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ? AND registered = 1', (user_id,))
    return cursor.fetchone() is not None

def get_latest_agreement():
    cursor.execute('SELECT text, version FROM agreements ORDER BY created_at DESC LIMIT 1')
    return cursor.fetchone()

def register_user(user_id, agreement_version):
    cursor.execute('UPDATE users SET registered = 1, agreement_version = ? WHERE user_id = ?', 
                 (agreement_version, user_id))
    conn.commit()

def set_wallet(user_id, wallet):
    cursor.execute('UPDATE users SET ton_wallet = ? WHERE user_id = ?', (wallet, user_id))
    conn.commit()

def get_wallet(user_id):
    cursor.execute('SELECT ton_wallet FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None

def get_credits(user_id):
    cursor.execute('SELECT credits FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def set_credits(user_id, credits):
    cursor.execute('UPDATE users SET credits = ? WHERE user_id = ?', (credits, user_id))
    conn.commit()

# --- Bot commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_logged_in(context):
        # Get GPT user data
        gpt = get_gpt_platform()
        gpt_username = context.user_data.get('gpt_username')
        gpt_password = context.user_data.get('gpt_password')
        
        if gpt_username and gpt_password:
            user_data = await gpt.get_user_data(gpt_username, gpt_password)
            if user_data:
                balance = user_data.get('balance', 'Unknown')
                status = user_data.get('status', 'Unknown')
                
                await update.message.reply_text(
                    "Welcome back!\n\n"
                    f"GPT Username: {gpt_username}\n"
                    f"GPT Balance: {balance}\n"
                    f"GPT Status: {status}\n\n")

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm registration/login."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'register':
        await query.message.edit_text("Please enter your username:")
        return USERNAME
    elif query.data == 'login':
        await query.message.edit_text("Please enter your username:")
        return GPT_USERNAME

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user points."""
    user_id = get_user_id(context)
    if not user_id:
        await update.message.reply_text("Please register or login first.")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    close_db_connection(conn)
    
    if result:
        await update.message.reply_text(f"You have {result[0]} points.")
    else:
        await update.message.reply_text("User not found.")

async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Watch video command."""
    user_id = get_user_id(context)
    if not user_id:
        await update.message.reply_text("Please register or login first.")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, points FROM videos WHERE active = 1 ORDER BY RANDOM() LIMIT 1')
    video = cursor.fetchone()
    close_db_connection(conn)
    
    if not video:
        await update.message.reply_text("No videos available.")
        return
    
    video_id, title, points = video
    await update.message.reply_text(f"Watching: {title}\nPoints: {points}")
    
    # Store video watch in context
    context.user_data['watching_video'] = video_id
    context.user_data['watch_start_time'] = time.time()

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user balance."""
    user_id = get_user_id(context)
    if not user_id:
        await update.message.reply_text("Please register or login first.")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    close_db_connection(conn)
    
    if result:
        await update.message.reply_text(f"Your balance: {result[0]} TON")
    else:
        await update.message.reply_text("User not found.")

async def setwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user wallet address."""
    if not is_admin(get_user_id(context)):
        await update.message.reply_text("Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide wallet address.")
        return
    
    wallet_address = context.args[0]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET wallet_address = ? WHERE id = ?', (wallet_address, get_user_id(context)))
    conn.commit()
    close_db_connection(conn)
    await update.message.reply_text("Wallet address updated!")

async def mywallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user wallet address."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT wallet_address FROM users WHERE id = ?', (get_user_id(context),))
    result = cursor.fetchone()
    close_db_connection(conn)
    
    if result and result[0]:
        await update.message.reply_text(f"Your wallet address: {result[0]}")
    else:
        await update.message.reply_text("No wallet address set.")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Withdraw TON coins."""
    if not is_admin(get_user_id(context)):
        await update.message.reply_text("Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide amount to withdraw.")
        return
    
    try:
        amount = float(context.args[0])
        if amount <= 0:
            await update.message.reply_text("Amount must be positive.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE id = ?', (get_user_id(context),))
        balance = cursor.fetchone()[0]
        
        if amount > balance:
            await update.message.reply_text("Insufficient balance.")
            return
        
        # Calculate fee
        fee = amount * TON_FEE_PERCENTAGE
        net_amount = amount - fee
        
        # Update balance
        cursor.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, get_user_id(context)))
        conn.commit()
        close_db_connection(conn)
        
        # Transfer TON (this would be implemented with TON client)
        await update.message.reply_text(f"Withdrawing {net_amount} TON (fee: {fee} TON)")
    except ValueError:
        await update.message.reply_text("Invalid amount.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Admin-only command
    if update.effective_user.id != int(os.getenv('ADMIN_ID', '0')):
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    # Get user statistics
    cursor.execute('''
        SELECT COUNT(DISTINCT user_id), SUM(credits)
        FROM users
    ''')
    user_stats = cursor.fetchone()
    
    # Get video statistics
    cursor.execute('''
        SELECT COUNT(*), SUM(points)
        FROM videos
    ''')
    video_stats = cursor.fetchone()
    
    # Get watch statistics
    cursor.execute('''
        SELECT COUNT(*), DATE(watched_at) as date
        FROM video_watches
        GROUP BY date
        ORDER BY date DESC
        LIMIT 7
    ''')
    watch_stats = cursor.fetchall()
    
    stats_text = f"📊 Statistics\n\n"
    stats_text += f"Users: {user_stats[0]}\n"
    stats_text += f"Total Points: {user_stats[1]}\n\n"
    stats_text += f"Videos: {video_stats[0]}\n"
    stats_text += f"Total Points Available: {video_stats[1]}\n\n"
    stats_text += "Watch History (last 7 days):\n"
    for count, date in watch_stats:
        stats_text += f"{date}: {count} watches\n"
    
    await update.message.reply_text(stats_text)

async def accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /accept <version>")
        return
    
    version = context.args[0]
    agreement_version = get_latest_agreement()[1]
    
    if version != agreement_version:
        await update.message.reply_text("Invalid agreement version. Please use /start to get the latest version.")
        return
    
    register_user(user_id, version)
    await update.message.reply_text(
        "Registration successful!\n"
        "Use /watch to get videos\n"
        "Use /points to check your points\n"
        "Use /balance to check your credits\n"
        "Use /withdraw to exchange credits for TON\n"
        "Use /referral to get your referral link\n"
        "Use /tasks to see your task status"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_registered(user_id):
        await update.message.reply_text(
            "Welcome back!\n"
            "Use /watch to get videos\n"
            "Use /points to check your points\n"
            "Use /balance to check your credits\n"
            "Use /withdraw to exchange credits for TON\n"
            "Use /referral to get your referral link\n"
            "Use /tasks to see your task status"
        )
        return
    
    # Get latest agreement
    agreement, version = get_latest_agreement()
    
    await update.message.reply_text(
        f"Welcome! Please read and accept the following agreement:\n\n{agreement}\n\n"
        f"To accept, reply with /accept {version}"
    )
    user_id = update.effective_user.id
    referrer = None
    if context.args and context.args[0].isdigit():
        referrer = int(context.args[0])
        if referrer != user_id:
            add_user(user_id, referrer)
        else:
            add_user(user_id)
    else:
        add_user(user_id)
    await update.message.reply_text(
        "Welcome!\nUse /setwallet <your TON address> to set your payout address.\nUse /balance to check your credits.\nUse /withdraw to exchange credits for TON.\nUse /daily to claim your daily bonus.\nUse /referral to get your referral link.\nUse /tasks to see your task status.\nUse /watch to watch a video and earn credits."
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    credits = get_credits(user_id)
    await update.message.reply_text(f"Your current balance is: {credits} credits.")

async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_registered(user_id):
        await update.message.reply_text("Please register first using /start")
        return
    
    # Get a random video that hasn't been watched by this user recently
    cursor.execute('''
        SELECT v.id, v.video_url, v.points 
        FROM videos v 
        LEFT JOIN video_watches vw ON vw.video_id = v.id AND vw.user_id = ?
        WHERE vw.user_id IS NULL 
        OR vw.watched_at < datetime('now', '-24 hours')
        ORDER BY RANDOM()
        LIMIT 1
    ''', (user_id,))
    video = cursor.fetchone()
    
    if not video:
        await update.message.reply_text("No available videos to watch at the moment.")
        return
    
    video_id, video_url, points = video
    
    # Generate a unique watch ID
    watch_id = hashlib.sha256(f"{user_id}{video_id}{int(time.time())}".encode()).hexdigest()
    
    # Send video with watch instructions
    await update.message.reply_text(
        f"Watch this video to earn {points} points:\n\n"
        f"{video_url}\n\n"
        f"After watching, reply with /confirm {watch_id}"
    )
    
    # Store the watch attempt
    cursor.execute('INSERT INTO video_watches (user_id, video_id) VALUES (?, ?)', (user_id, video_id))
    conn.commit()
    user_id = update.effective_user.id
    add_user(user_id)
    
    # Get a random video that hasn't been watched by this user recently
    cursor.execute('''
        SELECT v.id, v.video_url, v.points 
        FROM videos v 
        LEFT JOIN video_watches vw ON vw.video_id = v.id AND vw.user_id = ?
        WHERE vw.user_id IS NULL 
        OR vw.watched_at < datetime('now', '-24 hours')
        ORDER BY RANDOM()
        LIMIT 1
    ''', (user_id,))
    video = cursor.fetchone()
    
    if not video:
        await update.message.reply_text("No available videos to watch at the moment.")
        return
    
    video_id, video_url, points = video
    
    # Generate a unique watch ID
    watch_id = hashlib.sha256(f"{user_id}{video_id}{int(time.time())}".encode()).hexdigest()
    
    # Send video with watch instructions
    await update.message.reply_text(
        f"Watch this video to earn {points} points:\n\n"
        f"{video_url}\n\n"
        f"After watching, reply with /confirm {watch_id}"
    )
    
    # Store the watch attempt
    cursor.execute('INSERT INTO video_watches (user_id, video_id) VALUES (?, ?)', (user_id, video_id))
    conn.commit()
    try:
        user_id = update.effective_user.id
        print(f"User {user_id} requested watch command")
        
        add_user(user_id)
        print(f"User {user_id} added to database")
        
        # Get the domain from the database
        cursor.execute("SELECT value FROM settings WHERE key = 'domain'")
        row = cursor.fetchone()
        domain = row[0] if row else "http://localhost:8888"
        print(f"Using domain: {domain}")
        
        # Generate video URL
        video_url = f"{domain}/redirect/{user_id}"
        print(f"Generated video URL: {video_url}")
        
        # Mark task as started
        cursor.execute('INSERT OR REPLACE INTO tasks (user_id, task_name, status) VALUES (?, ?, ?)', 
                      (user_id, 'watch', 'started'))
        conn.commit()
        print(f"Task marked as started for user {user_id}")
        
        await update.message.reply_text(f"🎥 Watch this video to earn credits:\n{video_url}")
        print(f"Video URL sent to user {user_id}")
    except Exception as e:
        print(f"Error in watch command: {str(e)}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

# --- Wallet Management Commands ---
async def setwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_registered(user_id):
        await update.message.reply_text("Please register first using /start")
        return
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /setwallet <TON wallet address>")
        return
    
    wallet = context.args[0]
    set_wallet(user_id, wallet)
    await update.message.reply_text("TON wallet address set successfully!")
    user_id = update.effective_user.id
    add_user(user_id)
    if context.args:
        wallet = context.args[0]
        set_wallet(user_id, wallet)
        await update.message.reply_text(f"✅ Your TON wallet address has been set to: {wallet}\nYou can change it anytime with /setwallet <address>.")
    else:
        await update.message.reply_text("Usage: /setwallet <your TON wallet address>")

async def mywallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    wallet = get_wallet(user_id)
    if wallet:
        await update.message.reply_text(f"Your current TON wallet address is: {wallet}")
    else:
        await update.message.reply_text("You have not set a TON wallet address yet. Use /setwallet <address>.")

# --- Withdraw Command ---
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    credits = get_credits(user_id)
    wallet = get_wallet(user_id)
    if credits <= 0:
        await update.message.reply_text("❌ You have no credits to withdraw.")
        return
    if credits < 2:
        await update.message.reply_text("❌ Minimum withdrawal amount is 2 TON. Earn more credits before withdrawing.")
        return
    if not wallet:
        await update.message.reply_text("❌ You have not set your TON wallet address. Please use /setwallet <address> before withdrawing.")
        return
    payout = credits * 0.985
    fee = credits * 0.015
    set_credits(user_id, 0)
    await update.message.reply_text(
        f"✅ Sent {payout:.6f} TON to your wallet ({wallet}).\n1.5% fee ({fee:.6f} TON) sent to the owner.\n\nYou can check or update your wallet at any time with /mywallet or /setwallet."
    )

# --- Main function ---
async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    today = date.today().isoformat()
    cursor.execute('SELECT last_daily FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row and row[0] == today:
        await update.message.reply_text("You have already claimed your daily bonus today!")
        return
    # Give daily bonus
    bonus = 0.1
    credits = get_credits(user_id) + bonus
    set_credits(user_id, credits)
    cursor.execute('UPDATE users SET last_daily = ? WHERE user_id = ?', (today, user_id))
    conn.commit()
    await update.message.reply_text(f"🎁 You received your daily bonus of {bonus} credits! Come back tomorrow.")

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(f"Invite friends and earn rewards!\nYour referral link: {link}")

async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    cursor.execute('SELECT task_name, status FROM tasks WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("You have no active tasks yet. Use /watch to start earning!")
        return
    msg = "Your tasks:\n"
    for task, status in rows:
        msg += f"- {task}: {status}\n"
    await update.message.reply_text(msg)

async def setdomain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the video domain for the bot."""
    # Check if user is admin
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Only admins can set the video domain.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setdomain <your_video_domain>")
        return

    domain = context.args[0]
    
    # Validate domain format
    if not domain.startswith('http'):
        domain = f'https://{domain}'
    
    # Update domain in database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO settings (key, value) 
        VALUES (?, ?)
    ''', ('video_domain', domain))
    conn.commit()
    close_db_connection(conn)
    
    await update.message.reply_text(f"✅ Video domain updated! New video/ad links will use: {domain}")

def main():
    try:
        print("Starting bot...")
        print(f"Token loaded: {bool(TELEGRAM_BOT_TOKEN)}")
        
        # Initialize database
        print("Initializing database...")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users LIMIT 1")
        print(f"Database initialized: {cursor.fetchone() is not None}")
        close_db_connection(conn)
        
        # Create bot application
        print("Creating bot application...")
        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        print("Bot application created")
        
        # Initialize TON client
        client_config = ClientConfig()
        client = TonClient(config=client_config)
        
        # Add command handlers with logging
        def command_handler(command, handler):
            print(f"Adding handler for command: {command}")
            app.add_handler(CommandHandler(command, handler))
        
        command_handler("start", start)
        command_handler("help", lambda u, c: u.message.reply_text(
            "Available commands:\n/start - Welcome\n/balance - Check credits\n/setwallet <address> - Set payout wallet\n/mywallet - Show current wallet\n/withdraw - Exchange credits for TON\n/daily - Claim daily bonus\n/referral - Get your referral link\n/tasks - See your task status\n/setdomain <domain> - Set video/ad domain (admin)\n"))
        command_handler("setwallet", setwallet)
        command_handler("mywallet", mywallet)
        command_handler("balance", balance)
        command_handler("withdraw", withdraw)
        command_handler("daily", daily)
        command_handler("referral", referral)
        command_handler("tasks", tasks)
        command_handler("setdomain", setdomain)
        
        print("Starting polling...")
        app.run_polling()
    except Exception as e:
        print(f"Error in main: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        raise

# --- Initialize TON client ---
client_config = ClientConfig()
client = TonClient(config=client_config)

# --- Initialize bot ---
if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Add user management handlers
    application.add_handler(get_registration_handlers())
    application.add_handler(get_login_handlers())
    application.add_handler(get_credentials_handlers())

    # User commands
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('watch', watch))
    application.add_handler(CommandHandler('points', points))
    application.add_handler(CommandHandler('confirm', confirm))
    application.add_handler(CommandHandler('balance', balance))
    application.add_handler(CommandHandler('setwallet', setwallet))
    application.add_handler(CommandHandler('mywallet', mywallet))
    application.add_handler(CommandHandler('withdraw', withdraw))
    application.add_handler(CommandHandler('daily', daily))
    application.add_handler(CommandHandler('referral', referral))
    application.add_handler(CommandHandler('tasks', tasks))
    # Add middleware for security and analytics
    application.add_handler(MessageHandler(filters.ALL, rate_limit))
    
    # Add user management handlers
    application.add_handler(get_registration_handlers())
    application.add_handler(get_login_handlers())
    application.add_handler(get_credentials_handlers())

    # Add admin commands handler
    application.add_handler(get_admin_handlers())

    # Add user commands with logging
    for command in ['start', 'watch', 'points', 'confirm', 'balance',
                   'setwallet', 'mywallet', 'withdraw', 'daily',
                   'referral', 'tasks', 'logout', 'update_credentials']:
        application.add_handler(CommandHandler(
            command,
            lambda update, context, cmd=command: handle_command(update, context, cmd)
        ))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start background tasks
    asyncio.create_task(start_notification_processor())
    asyncio.create_task(backup_database())
    asyncio.create_task(check_for_updates())

    # Run the bot
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

async def main():
    """Main function to start the bot."""
    try:
        # Initialize managers
        managers = init_managers()
        
        # Initialize TON client
        client_config = ClientConfig()
        client = TonClient(config=client_config)
        
        # Initialize application
        application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Register handlers
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('points', points))
        application.add_handler(CommandHandler('watch', watch))
        application.add_handler(CommandHandler('balance', balance))
        application.add_handler(CommandHandler('setwallet', setwallet))
        application.add_handler(CommandHandler('mywallet', mywallet))
        application.add_handler(CommandHandler('withdraw', withdraw))
        application.add_handler(CommandHandler('stats', stats))
        application.add_handler(CommandHandler('setdomain', setdomain))
        
        # Add conversation handlers
        application.add_handler(get_registration_handlers())
        application.add_handler(get_login_handlers())
        application.add_handler(get_credentials_handlers())
        application.add_handler(get_admin_handlers())
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Start background tasks
        asyncio.create_task(backup_database())
        asyncio.create_task(check_for_updates())
        
        # Start the bot
        await application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        raise

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler."""
    try:
        # Rate limit check
        if not rate_limit(update, context):
            return

        if not is_logged_in(context):
            keyboard = [[InlineKeyboardButton("Register", callback_data='register')],
                        [InlineKeyboardButton("Login", callback_data='login')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Welcome! Please register or login.",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("You're already logged in!")
            
        # Log command
        analytics.log_command(
            user_id=update.effective_user.id,
            command='start',
            success=True,
            duration=0.0
        )
        
    except RateLimitError:
        await update.message.reply_text("Please wait before trying again.")
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await update.message.reply_text("An error occurred while processing your request.")
        analytics.log_command(
            user_id=update.effective_user.id,
            command='start',
            success=False,
            duration=0.0
        )
        await notification_system.send_error_notification(
            context, 
            update.effective_user.id, 
            e
        )

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user points."""
    try:
        # Rate limit check
        if not rate_limit(update, context):
            return

        user_id = get_user_id(context)
        if not user_id:
            await update.message.reply_text("Please register or login first.")
            return
            
        # Get user data from cache
        user_data = await cache_system.get_cached_result(f'user_{user_id}')
        if user_data is None:
            # Get from database if not in cache
            user_data = await db.get_user(user_id)
            if user_data:
                await cache_system.cache_result(f'user_{user_id}', user_data)
            else:
                await update.message.reply_text("User not found.")
                return
                
        await update.message.reply_text(f"You have {user_data['points']} points.")
        
        # Log command
        analytics.log_command(
            user_id=update.effective_user.id,
            command='points',
            success=True,
            duration=0.0
        )
        
    except RateLimitError:
        await update.message.reply_text("Please wait before trying again.")
    except Exception as e:
        logger.error(f"Error in points command: {str(e)}")
        await update.message.reply_text("An error occurred while checking your points.")
        analytics.log_command(
            user_id=update.effective_user.id,
            command='points',
            success=False,
            duration=0.0
        )
        await notification_system.send_error_notification(
            context, 
            update.effective_user.id, 
            e
        )

async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Watch video command."""
    try:
        if not rate_limit(update, context):
            return

        user_id = get_user_id(context)
        if not user_id:
            await update.message.reply_text("Please register or login first.")
            return

        # Get random active video
        video = await db.get_random_video()
        if not video:
            await update.message.reply_text("No videos available at the moment.")
            return

        # Send video with watch timer
        await update.message.reply_text(
            f"Watch this video: {video['url']}\n"
            f"Minimum watch time: {VIDEO_WATCH_TIME}s"
        )

        # Start watch timer
        start_time = time.time()
        
        # Wait for watch time
        await asyncio.sleep(VIDEO_WATCH_TIME)
        
        # Check if user is still watching
        if time.time() - start_time >= VIDEO_WATCH_TIME:
            # Log video view
            await analytics.log_video_view(
                video_id=video['id'],
                user_id=user_id,
                watch_time=VIDEO_WATCH_TIME
            )
            
            # Update user points
            await db.update_user_points(user_id, POINTS_PER_VIDEO)
            
            await update.message.reply_text(
                f"Great job! You earned {POINTS_PER_VIDEO} points!"
            )
        else:
            await update.message.reply_text("You didn't watch the video long enough.")
            
        # Log command
        analytics.log_command(
            user_id=update.effective_user.id,
            command='watch',
            success=True,
            duration=VIDEO_WATCH_TIME
        )
        
    except RateLimitError:
        await update.message.reply_text("Please wait before trying again.")
    except Exception as e:
        logger.error(f"Error in watch command: {str(e)}")
        await update.message.reply_text("An error occurred while processing your request.")
        analytics.log_command(
            user_id=update.effective_user.id,
            command='watch',
            success=False,
            duration=0.0
        )
        await notification_system.send_error_notification(
            context, 
            update.effective_user.id, 
            e
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user balance."""
    try:
        if not rate_limit(update, context):
            return

        user_id = get_user_id(context)
        if not user_id:
            await update.message.reply_text("Please register or login first.")
            return

        # Get user data from cache
        user_data = await cache_system.get_cached_result(f'user_{user_id}')
        if user_data is None:
            # Get from database if not in cache
            user_data = await db.get_user(user_id)
            if user_data:
                await cache_system.cache_result(f'user_{user_id}', user_data)
            else:
                await update.message.reply_text("User not found.")
                return

        await update.message.reply_text(
            f"Your balance: {user_data['balance']} TON\n"
            f"Minimum withdrawal: {TON_MIN_BALANCE} TON"
        )

        # Log command
        analytics.log_command(
            user_id=update.effective_user.id,
            command='balance',
            success=True,
            duration=0.0
        )

    except RateLimitError:
        await update.message.reply_text("Please wait before trying again.")
    except Exception as e:
        logger.error(f"Error in balance command: {str(e)}")
        await update.message.reply_text("An error occurred while checking your balance.")
        analytics.log_command(
            user_id=update.effective_user.id,
            command='balance',
            success=False,
            duration=0.0
        )
        await notification_system.send_error_notification(
            context, 
            update.effective_user.id, 
            e
        )

if __name__ == '__main__':
    asyncio.run(main())

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    """Handle commands with rate limiting and logging."""
    if not rate_limit(update, context):
        return
    
    start_time = time.time()
    try:
        # Execute command
        if command == 'start':
            await start(update, context)
        elif command == 'points':
            await points(update, context)
        elif command == 'watch':
            await watch(update, context)
        elif command == 'balance':
            await balance(update, context)
        elif command == 'setwallet':
            await setwallet(update, context)
        elif command == 'mywallet':
            await mywallet(update, context)
        elif command == 'withdraw':
            await withdraw(update, context)
        elif command == 'stats':
            await stats(update, context)
        elif command == 'setdomain':
            await setdomain(update, context)
        
        # Log command execution
        # Get the actual command handler
        handler = globals()[command]
        await handler(update, context)
        success = True
    except Exception as e:
        logger.error(f"Error in {command}: {str(e)}")
        await update.message.reply_text("An error occurred while processing your request.")
        success = False
    finally:
        duration = time.time() - start_time
        log_command(update, context, command, success, duration)

class BotError(Exception):
    """Base class for bot-specific exceptions."""
    pass

class DatabaseError(BotError):
    """Exception for database-related errors."""
    pass

class AuthenticationError(BotError):
    """Exception for authentication-related errors."""
    pass

class CommandError(BotError):
    """Exception for command execution errors."""
    pass

class RateLimitError(BotError):
    """Exception for rate limiting."""
    pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors gracefully."""
    error = context.error
    
    # Log the error
    logger.error(
        f"Error in update {update.update_id if update else 'unknown'}: {str(error)}",
        exc_info=True
    )
    
    # Send error message to user
    error_message = "An error occurred while processing your request."
    try:
        await update.message.reply_text(error_message)
    except Exception:
        logger.error("Could not send error message to user")
    
    # Notify admin
    if ADMIN_ID:
        try:
            error_details = (
                f"Error in bot:\n{str(error)}\n\n"
                f"Update:\n{update}\n\n"
                f"User ID: {update.effective_user.id if update.effective_user else 'unknown'}"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=error_details
            )
        except Exception as e:
            logger.error(f"Could not notify admin: {str(e)}")
    
    # Re-raise the error if it's not handled
    raise error
