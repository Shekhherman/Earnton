import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '666042316'))
TON_API_KEY = os.getenv('TON_API_KEY')
TON_API_URL = os.getenv('TON_API_URL', 'https://api.ton.org/v3')

# Validate required environment variables
required_env_vars = ['TELEGRAM_BOT_TOKEN', 'TON_API_KEY']
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"Required environment variable {var} is not set")

# Database Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'botdata.db')

# Rate Limiting
RATE_LIMIT = 5  # max attempts per hour
RATE_LIMIT_PERIOD = 3600  # 1 hour in seconds

# Constants
USERNAME, PASSWORD, GPT_USERNAME, GPT_PASSWORD, CONFIRM_UPDATE = range(5)

# TON Configuration
TON_FEE_PERCENTAGE = 0.015  # 1.5% fee
TON_MIN_BALANCE = 0.01  # Minimum balance in TON

# Video Configuration
VIDEO_WATCH_TIME = 30  # Minimum watch time in seconds
POINTS_PER_VIDEO = 10  # Points awarded per video

# Referral System
REFERRAL_BONUS = 50  # Points for successful referral
REFERRAL_LEVELS = 3  # Number of referral levels
