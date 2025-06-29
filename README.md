# TON Reward Bot

A Telegram bot that rewards users with TON cryptocurrency for watching videos.

## Features

- User registration and login system
- GPT platform integration
- Video watching with point rewards
- TON wallet management
- Daily bonus system
- Referral program
- Video categories and recommendations
- Leaderboard system

## Setup

1. Clone the repository:
```bash
git clone [your-repo-url]
cd ton-reward-bot
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```bash
cp .env.example .env
```

5. Edit `.env` with your credentials:
- TELEGRAM_BOT_TOKEN
- ADMIN_ID
- TON_WALLET_ADDRESS

## Running Locally

```bash
python bot.py
```

## Deployment

1. Install Heroku CLI:
```bash
brew install heroku
```

2. Login to Heroku:
```bash
heroku login
```

3. Create Heroku app:
```bash
heroku create ton-reward-bot
```

4. Set environment variables:
```bash
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set ADMIN_ID=your_admin_id
heroku config:set TON_WALLET_ADDRESS=your_wallet
```

5. Deploy:
```bash
git push heroku main
```

## Commands

- `/start` - Start the bot
- `/register` - Register new account
- `/login` - Login to your account
- `/watch` - Get videos to watch
- `/points` - Check your points
- `/balance` - Check your balance
- `/setwallet` - Set TON wallet address
- `/withdraw` - Withdraw TON
- `/daily` - Claim daily bonus
- `/referral` - Get referral link
- `/tasks` - View your tasks
- `/logout` - Logout from account
- `/update_credentials` - Update GPT credentials
- `/upload` - Upload video (admin only)
- `/stats` - View bot statistics (admin only)
- `/setdomain` - Set domain (admin only)

## Requirements

- Python 3.9.7
- Heroku account
- Telegram bot token
- TON wallet address
