# API Documentation

## Overview

The TON Reward Bot API provides endpoints for managing users, videos, and rewards.

## Authentication

All API endpoints require authentication using an API token.

### Headers
```
Authorization: Bearer YOUR_API_TOKEN
```

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
    "balance": "float"
}
```

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
