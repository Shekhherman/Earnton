# Troubleshooting Guide

## Common Issues and Solutions

### Bot Not Responding
1. Check if the bot is running:
   ```bash
   python bot.py
   ```
2. Verify environment variables:
   ```bash
   echo $TELEGRAM_BOT_TOKEN
   ```
3. Check logs:
   ```bash
   heroku logs --tail
   ```

### Database Connection Issues
1. Verify database file exists:
   ```bash
   ls -l botdata.db
   ```
2. Check database permissions:
   ```bash
   chmod 664 botdata.db
   ```
3. Initialize database:
   ```bash
   python db_setup.py
   ```

### GPT Platform Integration Issues
1. Verify credentials:
   ```bash
   python -c "from gpt_platform import GPTPlatform; print(GPTPlatform().validate_credentials('username', 'password'))"
   ```
2. Check API endpoint:
   ```bash
   curl -X GET https://gpt-platform.com/api/status
   ```

### Deployment Issues
1. Heroku deployment errors:
   - Check build logs:
     ```bash
     heroku logs --tail
     ```
   - Verify requirements.txt:
     ```bash
     cat requirements.txt
     ```
   - Check environment variables:
     ```bash
     heroku config
     ```

### Permission Errors
1. Fix file permissions:
   ```bash
   chmod +x bot.py
   chmod 664 botdata.db
   ```
2. Fix directory permissions:
   ```bash
   chmod 755 .
   ```

### Memory Issues
1. Monitor memory usage:
   ```bash
   heroku ps
   ```
2. Check worker dyno size:
   ```bash
   heroku ps:scale worker=1:Standard-1X
   ```

### Rate Limiting
1. Check Telegram API limits:
   - 30 messages per second per group
   - 20 messages per minute per user
2. Implement rate limiting:
   ```python
   from aiogram.utils.exceptions import Throttled
   try:
       await message.answer("Your message")
   except Throttled:
       pass
   ```

### Debugging Tips
1. Enable debug logging:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```
2. Use logging:
   ```python
   logger.info("Debug message")
   logger.error("Error message")
   ```
3. Add try-catch blocks:
   ```python
   try:
       # your code
   except Exception as e:
       logger.error(f"Error: {str(e)}")
   ```

## Error Messages and Solutions

### "Invalid Bot Token"
1. Verify token format:
   - Must start with "bot"
   - Must be 48 characters long
2. Check for typos
3. Verify token permissions

### "Database Error"
1. Check database file:
   ```bash
   file botdata.db
   ```
2. Verify file size:
   ```bash
   ls -lh botdata.db
   ```
3. Check database version:
   ```bash
   sqlite3 botdata.db ".schema"
   ```

### "Connection Error"
1. Check internet connection
2. Verify API endpoints
3. Check firewall settings
4. Use proxy if needed

## Performance Optimization

### Memory Usage
1. Use context managers:
   ```python
   with sqlite3.connect('botdata.db') as conn:
       # your code
   ```
2. Close connections:
   ```python
   conn.close()
   ```
3. Use async functions:
   ```python
   async def your_function():
       # your code
   ```

### Response Time
1. Use caching:
   ```python
   from functools import lru_cache
   @lru_cache(maxsize=128)
   def get_data():
       # your code
   ```
2. Batch operations:
   ```python
   async def process_batch():
       # process multiple items at once
   ```
3. Use async/await:
   ```python
   async def your_function():
       await asyncio.gather(
           task1(),
           task2(),
           task3()
       )
   ```
