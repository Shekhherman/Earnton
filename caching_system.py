import os
import logging
import time
import json
from typing import Dict, Any, Optional, Callable
import functools
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Cache:
    def __init__(self, cache_dir: str, max_size: int = 1024 * 1024 * 100):  # 100MB default
        self.cache_dir = cache_dir
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.initialize_cache_dir()

    def initialize_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def get_cache_size(self) -> int:
        """Get current cache size in bytes."""
        size = 0
        for file in os.listdir(self.cache_dir):
            try:
                size += os.path.getsize(os.path.join(self.cache_dir, file))
            except:
                continue
        return size

    def cleanup_cache(self):
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
                os.remove(os.path.join(self.cache_dir, key))
                del self.cache[key]
            except:
                continue

    def cache_key(self, func: Callable, *args, **kwargs) -> str:
        """Generate unique cache key for function call."""
        key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
        return key

    def cache_result(self, key: str, result: Any, ttl: int = 3600):
        """Cache a result with TTL."""
        cache_file = os.path.join(self.cache_dir, key)
        
        try:
            # Save result to file
            with open(cache_file, 'w') as f:
                json.dump({
                    'result': result,
                    'expires': int(time.time()) + ttl,
                    'last_access': int(time.time())
                }, f)
            
            # Update in-memory cache
            self.cache[key] = {
                'result': result,
                'expires': int(time.time()) + ttl,
                'last_access': int(time.time())
            }
            
            self.cleanup_cache()
        except Exception as e:
            logger.error(f"Error caching result: {str(e)}")

    def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result if it exists and hasn't expired."""
        cache_file = os.path.join(self.cache_dir, key)
        
        try:
            if key not in self.cache:
                # Load from file if not in memory
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                self.cache[key] = data
            else:
                data = self.cache[key]
            
            # Check if expired
            if data['expires'] < int(time.time()):
                os.remove(cache_file)
                del self.cache[key]
                return None
            
            # Update last access time
            data['last_access'] = int(time.time())
            self.cache[key] = data
            
            return data['result']
        except Exception as e:
            logger.error(f"Error getting cached result: {str(e)}")
            return None

    def cache_decorator(self, ttl: int = 3600):
        """Decorator to cache function results."""
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                key = self.cache_key(func, *args, **kwargs)
                
                # Try to get from cache
                result = self.get_cached_result(key)
                if result is not None:
                    return result
                
                # Call function and cache result
                result = func(*args, **kwargs)
                self.cache_result(key, result, ttl)
                return result
            return wrapper
        return decorator

def cache(ttl: int = 3600):
    """Decorator factory for caching."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
            
            # Create cache instance
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
