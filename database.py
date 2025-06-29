import sqlite3
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from config import DB_PATH

class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._connection = None

    @contextmanager
    def connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()) -> int:
        """Execute a query and return the last row ID."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row as dictionary."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetchall(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows as list of dictionaries."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def begin_transaction(self):
        """Begin a transaction."""
        with self.connection() as conn:
            conn.execute('BEGIN TRANSACTION')
            return conn

    def commit(self, conn: sqlite3.Connection):
        """Commit a transaction."""
        conn.commit()

    def rollback(self, conn: sqlite3.Connection):
        """Rollback a transaction."""
        conn.rollback()

    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID."""
        return self.fetchone(
            'SELECT * FROM users WHERE telegram_id = ?',
            (telegram_id,)
        )

    def create_user(self, telegram_id: int, username: str) -> int:
        """Create a new user."""
        return self.execute(
            '''
            INSERT INTO users (telegram_id, username)
            VALUES (?, ?)
            ''',
            (telegram_id, username)
        )

    def update_user(self, user_id: int, **kwargs) -> None:
        """Update user fields."""
        if not kwargs:
            return

        # Build SET clause
        set_clause = ', '.join(f'{field} = ?' for field in kwargs)
        params = tuple(kwargs.values()) + (user_id,)

        self.execute(
            f'UPDATE users SET {set_clause} WHERE id = ?',
            params
        )

    def get_video(self, video_id: int) -> Optional[Dict[str, Any]]:
        """Get video by ID."""
        return self.fetchone(
            'SELECT * FROM videos WHERE id = ?',
            (video_id,)
        )

    def get_random_video(self) -> Optional[Dict[str, Any]]:
        """Get a random active video."""
        return self.fetchone(
            'SELECT * FROM videos WHERE active = 1 ORDER BY RANDOM() LIMIT 1'
        )

    def log_video_view(self, video_id: int, user_id: int, watch_time: float) -> None:
        """Log a video view."""
        self.execute(
            '''
            INSERT INTO video_views (video_id, user_id, watch_time)
            VALUES (?, ?, ?)
            ''',
            (video_id, user_id, watch_time)
        )

    def get_user_points(self, user_id: int) -> int:
        """Get user's total points."""
        result = self.fetchone(
            'SELECT points FROM users WHERE id = ?',
            (user_id,)
        )
        return result['points'] if result else 0

    def update_user_points(self, user_id: int, points: int) -> None:
        """Update user's points."""
        self.execute(
            'UPDATE users SET points = points + ? WHERE id = ?',
            (points, user_id)
        )

    def get_user_balance(self, user_id: int) -> float:
        """Get user's balance."""
        result = self.fetchone(
            'SELECT balance FROM users WHERE id = ?',
            (user_id,)
        )
        return result['balance'] if result else 0.0

    def update_user_balance(self, user_id: int, amount: float) -> None:
        """Update user's balance."""
        self.execute(
            'UPDATE users SET balance = balance + ? WHERE id = ?',
            (amount, user_id)
        )

# Initialize database instance
db = Database()
