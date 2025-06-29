import os
from typing import Dict, Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Default values
        self.defaults = {
            'TELEGRAM_BOT_TOKEN': '',
            'ADMIN_ID': '',
            'TON_API_KEY': '',
            'TON_API_URL': '',
            'DB_PATH': 'botdata.db',
            'RATE_LIMIT_PERIOD': 60,
            'RATE_LIMIT': 5,
            'TON_FEE_PERCENTAGE': 0.015,
            'TON_MIN_BALANCE': 0.01,
            'VIDEO_WATCH_TIME': 30,
            'POINTS_PER_VIDEO': 10,
            'REFERRAL_BONUS': 50,
            'REFERRAL_LEVELS': 3
        }
        
        # Load configuration
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from environment variables."""
        self.config = {}
        for key, default in self.defaults.items():
            value = os.getenv(key, default)
            # Convert to appropriate type
            if isinstance(default, int):
                value = int(value)
            elif isinstance(default, float):
                value = float(value)
            elif isinstance(default, bool):
                value = value.lower() == 'true'
            self.config[key] = value

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def validate(self) -> bool:
        """Validate configuration values."""
        errors = []
        
        # Validate required fields
        required = ['TELEGRAM_BOT_TOKEN', 'ADMIN_ID', 'TON_API_KEY', 'TON_API_URL']
        for field in required:
            value = self.config.get(field)
            if not value:
                errors.append(f"Missing required configuration: {field}")
                continue
                
            if field == 'TELEGRAM_BOT_TOKEN':
                if not value.startswith('bot'):
                    errors.append("Invalid TELEGRAM_BOT_TOKEN format")
            elif field == 'ADMIN_ID':
                try:
                    int(value)
                except ValueError:
                    errors.append("ADMIN_ID must be an integer")
            elif field == 'TON_API_KEY':
                if len(value) < 32:
                    errors.append("TON_API_KEY is too short")
            elif field == 'TON_API_URL':
                if not value.startswith(('http://', 'https://')):
                    errors.append("TON_API_URL must be a valid URL")
        
        # Validate numeric fields
        numeric_fields = {
            'RATE_LIMIT_PERIOD': {'type': int, 'min': 30, 'max': 3600},
            'RATE_LIMIT': {'type': int, 'min': 1, 'max': 100},
            'TON_FEE_PERCENTAGE': {'type': float, 'min': 0.0, 'max': 0.1},
            'TON_MIN_BALANCE': {'type': float, 'min': 0.01, 'max': 1000.0},
            'VIDEO_WATCH_TIME': {'type': int, 'min': 10, 'max': 300},
            'POINTS_PER_VIDEO': {'type': int, 'min': 1, 'max': 100},
            'REFERRAL_BONUS': {'type': int, 'min': 1, 'max': 1000},
            'REFERRAL_LEVELS': {'type': int, 'min': 1, 'max': 10}
        }
        
        for field, rules in numeric_fields.items():
            value = self.config.get(field)
            if not isinstance(value, rules['type']):
                errors.append(f"{field} must be a {rules['type'].__name__}")
                continue
                
            if value < rules['min'] or value > rules['max']:
                errors.append(
                    f"{field} must be between {rules['min']} and {rules['max']}")
        
        # Validate database path
        db_path = self.config.get('DB_PATH')
        if not db_path:
            errors.append("DB_PATH is required")
        elif not db_path.endswith('.db'):
            errors.append("DB_PATH must end with .db extension")
        
        if errors:
            logger.error("Configuration validation errors:")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return self.config.copy()

# Initialize config manager
config_manager = ConfigManager()

# Validate configuration on startup
if not config_manager.validate():
    raise ValueError("Invalid configuration. Please check your environment variables.")
