# TON Reward Bot

A Telegram bot that rewards users with TON cryptocurrency for watching videos.

## Security

### Rate Limiting
- 60 requests per minute per user
- 1000 requests per hour per IP
- 10 bonus checks per hour
- 5 bonus claims per hour

### Input Validation
- Message length: 4096 characters
- File size: 50MB
- SQL injection prevention
- XSS protection
- CSRF protection

### Security Features
- Environment variable configuration
- S3 backup with encryption
- Secure password hashing
- Rate limiting middleware
- Message validation
- Error handling with logging
- Transaction management

### Error Handling
- All errors are logged
- Sensitive data is sanitized
- Retry mechanism (3 attempts with 1s delay)
- Transaction management

## Features

- User registration and login system
- GPT platform integration
- Video watching with point rewards
- TON wallet management
- Daily bonus system
- Referral program
- Video categories and recommendations
- Leaderboard system
- TON-based advertising system

## TON Payment System

### Creating Advertisements
1. Use `/createad [amount]` command to start the process
   - Optional: Specify amount in TON (default: 1.0 TON)
2. Bot will provide a TON payment address
3. Send TON to the provided address
4. After payment confirmation:
   - Send advertisement title as first line
   - Send description in subsequent lines
   - Attach media (photo or document)
5. Advertisement will be activated after payment confirmation

### Payment Security
- Minimum payment amount: 0.1 TON
- Payment timeout: 5 minutes
- Payment status updates in real-time
- Secure payment verification
- Automatic advertisement activation

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
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ADMIN_ID=your_admin_id
TON_API_KEY=your_ton_api_key
TON_API_URL=https://api.ton.org/v3
APP_BASE_URL=https://your-app-domain.com

# Security Settings
RATE_LIMIT=5
RATE_LIMIT_PERIOD=3600
TON_FEE_PERCENTAGE=0.015
TON_MIN_BALANCE=0.01

# Database Settings
DB_PATH=botdata.db
```

## Security Instructions

1. **Environment Variables**
   - Store all sensitive credentials in environment variables
   - Never commit `.env` file to version control
   - Use `.env.example` as a template

2. **Database Security**
   - Use parameterized queries to prevent SQL injection
   - Regular database backups
   - Proper error handling to prevent information leakage

3. **Rate Limiting**
   - Default rate limit: 5 requests per hour
   - Configure in `.env` file

4. **API Security**
   - Use HTTPS for all API endpoints
   - Validate API keys and tokens
   - Implement proper error handling

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
