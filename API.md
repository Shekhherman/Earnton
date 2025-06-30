# API Documentation

## Overview

The TON Reward Bot API provides endpoints for managing users, videos, and rewards.

## Security

### Rate Limiting
- 60 requests per minute per user
- 1000 requests per hour per IP
- Excessive requests will be blocked

### Security Headers
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Content-Security-Policy: default-src 'self'

### Input Validation
- All requests are validated for length and format
- File uploads are limited to 50MB
- Message length is limited to 4096 characters

## Authentication

All API endpoints require authentication using an API token and rate limiting.

### Headers
```
Authorization: Bearer YOUR_API_TOKEN
X-Rate-Limit-Limit: 60
X-Rate-Limit-Remaining: 59
X-Rate-Limit-Reset: 1628534400
```

### Error Responses
- 429 Too Many Requests
- 401 Unauthorized
- 403 Forbidden
- 400 Bad Request
- 500 Internal Server Error

## Endpoints

### User Management

#### Register User
```
POST /api/users/register
```

Request:
```json
{
    "username": "string",
    "password": "string",
    "gpt_username": "string",
    "gpt_password": "string"
}
```

Response:
```json
{
    "user_id": "integer",
    "username": "string",
    "points": "integer",
    "balance": "float",
    "next_daily_bonus": "iso8601_date"
}
```

### Security Features
- Rate limiting (10 checks per hour)
- Input validation
- SQL injection prevention
- XSS protection
- CSRF protection

### Error Handling
- All errors are logged
- Sensitive data is sanitized
- Retry mechanism (3 attempts with 1s delay)
- Transaction management

#### Login User
```
POST /api/users/login
```

Request:
```json
{
    "username": "string",
    "password": "string"
}
```

Response:
```json
{
    "user_id": "integer",
    "token": "string",
    "expires": "datetime"
}
```

### Video Management

#### Get Videos
```
GET /api/videos
```

Response:
```json
[
    {
        "id": "integer",
        "title": "string",
        "url": "string",
        "category": "string",
        "points": "integer"
    }
]
```

#### Upload Video
```
POST /api/videos/upload
```

Request:
```json
{
    "title": "string",
    "url": "string",
    "category": "integer",
    "points": "integer"
}
```

Response:
```json
{
    "video_id": "integer",
    "status": "success"
}
```

### Reward System

#### Get Points
```
GET /api/users/points
```

Response:
```json
{
    "total_points": "integer",
    "daily_bonus": "integer",
    "available_points": "integer"
}
```

#### Withdraw Points
```
POST /api/users/withdraw
```

Request:
```json
{
    "points": "integer",
    "wallet_address": "string"
}
```

Response:
```json
{
    "transaction_id": "string",
    "status": "pending",
    "amount": "float"
}
```

### GPT Integration

#### Validate Credentials
```
POST /api/gpt/validate
```

Request:
```json
{
    "username": "string",
    "password": "string"
}
```

Response:
```json
{
    "valid": "boolean",
    "user_data": {
        "balance": "float",
        "status": "string"
    }
}
```

### Leaderboard

#### Get Leaderboard
```
GET /api/leaderboard
```

Parameters:
- period: daily|weekly|monthly
- limit: integer

Response:
```json
[
    {
        "rank": "integer",
        "user_id": "integer",
        "username": "string",
        "points": "integer"
    }
]
```

### Error Responses

All endpoints may return error responses:
```json
{
    "error": "string",
    "code": "integer",
    "message": "string"
}
```

## Rate Limiting

- 30 requests per minute per IP
- 1000 requests per day per user
- 10 concurrent connections maximum

## Security

- All requests must use HTTPS
- Rate limiting enabled
- Input validation required
- SQL injection prevention
- XSS protection

## Versioning

API version is included in the URL:
```
/api/v1/
```

## Examples

### Register User
```bash
curl -X POST https://api.ton-reward-bot.com/api/v1/users/register \
-H "Content-Type: application/json" \
-d '{
    "username": "user123",
    "password": "securepassword",
    "gpt_username": "gptuser",
    "gpt_password": "gptsecure"
}'
```

### Get Videos
```bash
curl https://api.ton-reward-bot.com/api/v1/videos \
-H "Authorization: Bearer YOUR_TOKEN"
```

## Best Practices

1. Always validate input
2. Handle errors gracefully
3. Use proper authentication
4. Follow rate limits
5. Secure sensitive data
6. Monitor API usage
7. Keep API version up to date
8. Document all changes
9. Test thoroughly
10. Follow security guidelines
