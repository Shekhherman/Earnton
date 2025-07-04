import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher
from aiogram.utils import executor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Earnton Bot"}

# Initialize bot
bot = Bot(token=os.getenv('BOT_TOKEN'))

def start_bot():
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
    
    dp = Dispatcher(bot)
    
    # Register handlers
    dp.include_router(get_registration_handlers())
    dp.include_router(get_login_handlers())
    dp.include_router(get_credentials_handlers())
    
    # Register commands
    dp.register_message_handler(start, commands=['start'])
    dp.register_message_handler(watch, commands=['watch'])
    dp.register_message_handler(points, commands=['points'])
    dp.register_message_handler(confirm, commands=['confirm'])
    dp.register_message_handler(balance, commands=['balance'])
    dp.register_message_handler(setwallet, commands=['setwallet'])
    dp.register_message_handler(mywallet, commands=['mywallet'])
    dp.register_message_handler(withdraw, commands=['withdraw'])
    dp.register_message_handler(daily, commands=['daily'])
    dp.register_message_handler(referral, commands=['referral'])
    dp.register_message_handler(tasks, commands=['tasks'])
    dp.register_message_handler(logout, commands=['logout'])
    dp.register_message_handler(update_credentials, commands=['update_credentials'])
    dp.register_message_handler(upload, commands=['upload'])
    dp.register_message_handler(stats, commands=['stats'])
    dp.register_message_handler(setdomain, commands=['setdomain'])
    
    return dp

@app.on_event("startup")
async def startup_event():
    global dp
    dp = start_bot()
    
    # Set webhook
    app_base_url = os.getenv('APP_BASE_URL')
    if not app_base_url:
        raise ValueError("APP_BASE_URL environment variable is not set")
    
    # Validate URL format
    if not app_base_url.startswith(('http://', 'https://')):
        raise ValueError("APP_BASE_URL must start with http:// or https://")
    
    webhook_url = f"{app_base_url}/webhook"
    await bot.set_webhook(webhook_url)

@app.post("/webhook")
async def webhook(request: Request):
    update = await request.json()
    asyncio.create_task(dp.process_update(update))
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('APP_PORT', 10000)))
