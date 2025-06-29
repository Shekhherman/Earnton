-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    gpt_username TEXT NOT NULL,
    gpt_password TEXT NOT NULL,
    points INTEGER DEFAULT 0,
    agreement_accepted BOOLEAN DEFAULT FALSE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_admin BOOLEAN DEFAULT FALSE
);

-- Registration attempts table
CREATE TABLE IF NOT EXISTS registration_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    step TEXT NOT NULL,
    attempt_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_type TEXT,
    error_message TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- User analytics table
CREATE TABLE IF NOT EXISTS user_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    event_type TEXT NOT NULL,
    event_data TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- TON transactions table
CREATE TABLE IF NOT EXISTS ton_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    transaction_id TEXT UNIQUE NOT NULL,
    amount DECIMAL(20,10) NOT NULL,
    status TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- GPT usage table
CREATE TABLE IF NOT EXISTS gpt_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    request_id TEXT UNIQUE NOT NULL,
    tokens_used INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Admin commands table
CREATE TABLE IF NOT EXISTS admin_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    command TEXT NOT NULL,
    parameters TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users (id)
);
