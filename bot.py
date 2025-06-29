import os
import sys
import logging
from dotenv import load_dotenv
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.utils import executor

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

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

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

async def main():
    # Set up commands
    await setup_commands(dp)

    # Add handlers
    dp.add_handler(get_registration_handlers())
    dp.add_handler(get_login_handlers())
    dp.add_handler(get_credentials_handlers())
    
    # Add command handlers
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('watch', watch))
    dp.add_handler(CommandHandler('points', points))
    dp.add_handler(CommandHandler('confirm', confirm))
    dp.add_handler(CommandHandler('balance', balance))
    dp.add_handler(CommandHandler('setwallet', setwallet))
    dp.add_handler(CommandHandler('mywallet', mywallet))
    dp.add_handler(CommandHandler('withdraw', withdraw))
    dp.add_handler(CommandHandler('daily', daily))
    dp.add_handler(CommandHandler('referral', referral))
    dp.add_handler(CommandHandler('tasks', tasks))
    dp.add_handler(CommandHandler('logout', logout))
    dp.add_handler(CommandHandler('update_credentials', update_credentials))
    
    # Admin handlers
    dp.add_handler(CommandHandler('upload', upload))
    dp.add_handler(CommandHandler('stats', stats))
    dp.add_handler(CommandHandler('setdomain', setdomain))

    # Start polling
    await dp.start_polling()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Bot error: {str(e)}")
