import os
import logging
import time
import json
from typing import Dict, Any, Optional, Callable, TypeVar, Generic, Awaitable, ParamSpec
import functools
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import aiofiles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheSystem:
    def __init__(self, cache_dir: str = 'cache'):
        """Initialize cache system."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache: Dict[str, dict] = {}
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self.lock = asyncio.Lock()

    async def _periodic_cleanup(self):
        """Periodically clean up expired cache entries."""
        while True:
            await asyncio.sleep(3600)  # Clean up every hour
            async with self.lock:
                await self.cleanup_expired()

    async def cleanup_expired(self):
        """Clean up expired cache entries."""
        now = datetime.now()
        
        # Clean up in-memory cache
        for key, entry in list(self.cache.items()):
            if entry['expiry'] < now:
                del self.cache[key]
        
        # Clean up cache files
        for file_path in self.cache_dir.glob('*.json'):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    expiry = datetime.fromisoformat(data['expiry'])
                    if expiry < now:
                        file_path.unlink()
            except Exception as e:
                logger.error(f"Error cleaning up cache file {file_path}: {str(e)}")
                continue

    async def get_cached_result(self, key: str) -> Optional[dict]:
        """Get cached result by key."""
        async with self.lock:
            # Check in-memory cache first
            if key in self.cache:
                entry = self.cache[key]
                if entry['expiry'] > datetime.now():
                    return entry['value']
            
            # Check cache file
            file_path = self.cache_dir / f"{key}.json"
            if not file_path.exists():
                return None
                
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    expiry = datetime.fromisoformat(data['expiry'])
                    
                    if expiry > datetime.now():
                        # Update in-memory cache
                        self.cache[key] = {
                            'value': data['value'],
                            'expiry': expiry
                        }
                        return data['value']
                    
            except Exception as e:
                logger.error(f"Error reading cache file {file_path}: {str(e)}")
                return None
                
            return None

    async def cache_result(self, key: str, value: dict, ttl: int = 3600) -> None:
        """Cache a result with TTL."""
        expiry = datetime.now() + timedelta(seconds=ttl)
        
        async with self.lock:
            # Update in-memory cache
            self.cache[key] = {
                'value': value,
                'expiry': expiry
            }
            
            # Write to cache file
            file_path = self.cache_dir / f"{key}.json"
            try:
                with open(file_path, 'w') as f:
                    json.dump({
                        'value': value,
                        'expiry': expiry.isoformat()
                    }, f)
            except Exception as e:
                logger.error(f"Error writing cache file {file_path}: {str(e)}")

    def cache_decorator(self, ttl: int = 3600):
        """Decorator to cache async function results."""
        P = ParamSpec('P')
        R = TypeVar('R')
        
        def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            @functools.wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                # Generate cache key from function name and arguments
                key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
                
                # Try to get from cache
                cached_result = await self.get_cached_result(key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.cache_result(key, result, ttl)
                return result
            
            return wrapper
        
        return decorator

    async def invalidate_cache(self, key: str) -> None:
        """Invalidate cache entry by key."""
        async with self.lock:
            # Remove from in-memory cache
            if key in self.cache:
                del self.cache[key]
                
            # Remove cache file
            file_path = self.cache_dir / f"{key}.json"
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.error(f"Error removing cache file {file_path}: {str(e)}")

    async def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        async with self.lock:
            # Remove matching in-memory cache entries
            for key in list(self.cache.keys()):
                if pattern in key:
                    del self.cache[key]
            
            # Remove matching cache files
            for file_path in self.cache_dir.glob('*.json'):
                if pattern in file_path.stem:
                    try:
                        file_path.unlink()
                    except Exception as e:
                        logger.error(f"Error removing cache file {file_path}: {str(e)}")

cache_system = CacheSystem()

def cache(ttl: int = 3600):
    """Decorator factory for caching."""
    return cache_system.cache_decorator(ttl)

class Cache(Generic[T]):
    def __init__(self, cache_dir: str, max_size: int = 1024 * 1024 * 100):  # 100MB default
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.initialize_cache_dir()
        self._cleanup_task: Optional[asyncio.Task] = None

    def initialize_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_size(self) -> int:
        """Get current cache size in bytes."""
        size = 0
        for file in self.cache_dir.glob('*'):
            try:
                size += file.stat().st_size
            except:
                continue
        return size

    async def cleanup_cache(self) -> None:
        """Remove oldest items to maintain max size."""
        if self.get_cache_size() <= self.max_size:
            return

        # Sort by last accessed time
        sorted_items = sorted(
            [(k, v['last_access']) for k, v in self.cache.items()],
            key=lambda x: x[1]
        )

        # Remove oldest items until we're under max size
        while self.get_cache_size() > self.max_size and sorted_items:
            key, _ = sorted_items.pop(0)
            try:
                (self.cache_dir / key).unlink()
                del self.cache[key]
            except:
                continue

    def cache_key(self, func: Callable, *args, **kwargs) -> str:
        """Generate unique cache key for function call."""
        key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
        return key

    async def cache_result(self, key: str, result: T, ttl: int = 3600) -> None:
        """Cache a result with TTL."""
        cache_file = self.cache_dir / key
        
        try:
            # Save result to file
            async with aiofiles.open(cache_file, 'w') as f:
                await f.write(json.dumps({
                    'result': result,
                    'expires': int(time.time()) + ttl,
                    'last_access': int(time.time())
                }))
            
            # Update in-memory cache
            self.cache[key] = {
                'result': result,
                'expires': int(time.time()) + ttl,
                'last_access': int(time.time())
            }
            
            await self.cleanup_cache()
        except Exception as e:
            logger.error(f"Error caching result: {str(e)}")

    async def get_cached_result(self, key: str) -> Optional[T]:
        """Get cached result if it exists and hasn't expired."""
        cache_file = self.cache_dir / key
        
        try:
            if key not in self.cache:
                # Load from file if not in memory
                async with aiofiles.open(cache_file, 'r') as f:
                    data = json.loads(await f.read())
                self.cache[key] = data
            else:
                data = self.cache[key]
            
            # Check if expired
            if data['expires'] < int(time.time()):
                await cache_file.unlink()
                del self.cache[key]
                return None
            
            # Update last access time
            data['last_access'] = int(time.time())
            self.cache[key] = data
            
            return data['result']
            
        except Exception as e:
            logger.error(f"Error getting cached result: {str(e)}")
            return None

    def start_cleanup_task(self) -> None:
        """Start background task for periodic cache cleanup."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        async def cleanup_loop():
            while True:
                try:
                    await self.cleanup_cache()
                    await asyncio.sleep(3600)  # Check every hour
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {str(e)}")
                    await asyncio.sleep(60)  # Wait before retrying
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            cached_result = await cache_system.get_cached_result(cache_key)
            
            if cached_result is not None:
                return cached_result
            cache = Cache(cache_dir)
            
            # Try to get from cache
            result = cache.get_cached_result(cache_key)
            if result is not None:
                return result
                
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.cache_result(cache_key, result, ttl)
            return result
        return wrapper
