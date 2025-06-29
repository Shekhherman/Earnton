# Database Schema Documentation

## Overview

The database schema for the TON Reward Bot consists of several tables that manage users, videos, rewards, and system settings.

## Tables

### Users
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    gpt_username TEXT NOT NULL,
    gpt_password_hash TEXT NOT NULL,
    points INTEGER DEFAULT 0,
    balance FLOAT DEFAULT 0.0,
    wallet_address TEXT,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_admin BOOLEAN DEFAULT FALSE,
    agreement_version TEXT,
    accepted_agreement BOOLEAN DEFAULT FALSE
);
```

### Videos
```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    category_id INTEGER NOT NULL,
    points INTEGER NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploader_id INTEGER,
    FOREIGN KEY (category_id) REFERENCES video_categories(id),
    FOREIGN KEY (uploader_id) REFERENCES users(id)
);
```

### Video Watches
```sql
CREATE TABLE video_watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    video_id INTEGER NOT NULL,
    watch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    points_awarded INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (video_id) REFERENCES videos(id),
    UNIQUE (user_id, video_id)
);
```

### Video Categories
```sql
CREATE TABLE video_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    points INTEGER NOT NULL,
    description TEXT
);
```

### Tasks
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    points INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Daily Bonuses
```sql
CREATE TABLE daily_bonuses (
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    points INTEGER NOT NULL,
    PRIMARY KEY (user_id, date),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Referrals
```sql
CREATE TABLE referrals (
    referrer_id INTEGER NOT NULL,
    referred_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    PRIMARY KEY (referrer_id, referred_id),
    FOREIGN KEY (referrer_id) REFERENCES users(id),
    FOREIGN KEY (referred_id) REFERENCES users(id)
);
```

### User Preferences
```sql
CREATE TABLE user_preferences (
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    preference_level INTEGER NOT NULL,
    PRIMARY KEY (user_id, category_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (category_id) REFERENCES video_categories(id)
);
```

### Leaderboard Entries
```sql
CREATE TABLE leaderboard_entries (
    user_id INTEGER NOT NULL,
    points INTEGER NOT NULL,
    date TEXT NOT NULL,
    PRIMARY KEY (user_id, date),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### User Achievements
```sql
CREATE TABLE user_achievements (
    user_id INTEGER PRIMARY KEY,
    total_points INTEGER DEFAULT 0,
    daily_wins INTEGER DEFAULT 0,
    weekly_wins INTEGER DEFAULT 0,
    monthly_wins INTEGER DEFAULT 0,
    last_win_date TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Relationships

### Users and Videos
- One user can watch multiple videos
- One video can be watched by multiple users
- Points are awarded for each video watch

### Users and Tasks
- One user can have multiple tasks
- Tasks have different types and statuses
- Points are awarded for completed tasks

### Videos and Categories
- One video belongs to one category
- Categories have different point values
- Users can have preferences for categories

## Indexes

```sql
CREATE INDEX idx_user_username ON users(username);
CREATE INDEX idx_video_category ON videos(category_id);
CREATE INDEX idx_video_watch_user ON video_watches(user_id);
CREATE INDEX idx_task_user ON tasks(user_id);
CREATE INDEX idx_referral_referrer ON referrals(referrer_id);
CREATE INDEX idx_leaderboard_date ON leaderboard_entries(date);
```

## Data Integrity

- All foreign key constraints are enforced
- Unique constraints prevent duplicates
- NOT NULL constraints ensure required fields
- Appropriate data types are used

## Maintenance

### Backups
- Daily full backups
- Hourly incremental backups
- Offsite storage

### Optimization
- Regular vacuuming
- Index maintenance
- Statistics update

### Monitoring
- Disk space usage
- Connection count
- Query performance
- Error tracking

## Best Practices

1. Use transactions for multiple operations
2. Validate data before insertion
3. Use prepared statements
4. Implement proper error handling
5. Regular maintenance
6. Backup verification
7. Performance monitoring
8. Security checks
9. Data validation
10. Documentation updates
