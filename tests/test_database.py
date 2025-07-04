import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from database import Database
from config_manager import config_manager

class TestDatabase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = Database(':memory:')
        
        # Create test tables
        await self.db.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                points INTEGER DEFAULT 0,
                balance REAL DEFAULT 0
            )
        ''')
        
        await self.db.execute('''
            CREATE TABLE videos (
                id INTEGER PRIMARY KEY,
                title TEXT,
                url TEXT UNIQUE,
                points INTEGER,
                active BOOLEAN DEFAULT TRUE
            )
        ''')

    async def test_get_user(self):
        """Test getting user."""
        # Insert test user
        await self.db.execute('''
            INSERT INTO users (telegram_id, username, points, balance)
            VALUES (?, ?, ?, ?)
        ''', (789, 'testuser', 100, 10.5))

        # Test getting user
        user = await self.db.get_user(789)
        self.assertIsNotNone(user)
        self.assertEqual(user['points'], 100)
        self.assertEqual(user['balance'], 10.5)

    async def test_create_user(self):
        """Test creating user."""
        user_id = await self.db.create_user(789, 'testuser')
        self.assertIsNotNone(user_id)

        # Verify user was created
        user = await self.db.get_user(789)
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'testuser')

    async def test_update_user(self):
        """Test updating user."""
        # Create test user
        await self.db.create_user(789, 'testuser')

        # Update user
        await self.db.update_user(789, points=50, balance=5.0)

        # Verify update
        user = await self.db.get_user(789)
        self.assertEqual(user['points'], 50)
        self.assertEqual(user['balance'], 5.0)

    async def test_get_random_video(self):
        """Test getting random video."""
        # Insert test videos
        await self.db.execute('''
            INSERT INTO videos (title, url, points, active)
            VALUES (?, ?, ?, ?)
        ''', ('Test Video 1', 'url1', 10, True))

        await self.db.execute('''
            INSERT INTO videos (title, url, points, active)
            VALUES (?, ?, ?, ?)
        ''', ('Test Video 2', 'url2', 15, True))

        # Get random video
        video = await self.db.get_random_video()
        self.assertIsNotNone(video)
        self.assertIn(video['url'], ['url1', 'url2'])

    async def test_log_video_view(self):
        """Test logging video view."""
        # Create test user and video
        await self.db.create_user(789, 'testuser')
        await self.db.execute('''
            INSERT INTO videos (title, url, points, active)
            VALUES (?, ?, ?, ?)
        ''', ('Test Video', 'url', 10, True))

        # Log video view
        await self.db.log_video_view(1, 789, 30.0)

        # Verify view was logged
        view = await self.db.fetchone('''
            SELECT * FROM video_views
            WHERE video_id = ? AND user_id = ?
        ''', (1, 789))
        self.assertIsNotNone(view)
        self.assertEqual(view['watch_time'], 30.0)

if __name__ == '__main__':
    unittest.main()
