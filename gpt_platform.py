import requests
import logging
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GPTPlatform:
    def __init__(self, base_url: str = "https://gpt-platform.com/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Telegram Bot/1.0',
            'Accept': 'application/json'
        })

    def validate_credentials(self, username: str, password: str) -> bool:
        """
        Validate GPT platform credentials.
        
        Args:
            username: GPT platform username
            password: GPT platform password
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            url = f"{self.base_url}/user_data"
            payload = {
                'username': username,
                'password': password
            }
            
            response = self.session.post(url, data=payload)
            response.raise_for_status()
            
            if response.status_code == 200:
                data = response.json()
                return data.get('success', False)
            return False
            
        except requests.RequestException as e:
            logger.error(f"Error validating credentials: {str(e)}")
            return False

    def get_user_data(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Get user data from GPT platform.
        
        Args:
            username: GPT platform username
            password: GPT platform password
            
        Returns:
            dict: User data if successful, None otherwise
        """
        try:
            if not self.validate_credentials(username, password):
                return None
                
            url = f"{self.base_url}/user_data"
            payload = {
                'username': username,
                'password': password
            }
            
            response = self.session.post(url, data=payload)
            response.raise_for_status()
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error getting user data: {str(e)}")
            return None

    def get_user_balance(self, username: str, password: str) -> Optional[float]:
        """
        Get user's balance from GPT platform.
        
        Args:
            username: GPT platform username
            password: GPT platform password
            
        Returns:
            float: User's balance if successful, None otherwise
        """
        user_data = self.get_user_data(username, password)
        if user_data and isinstance(user_data.get('balance'), (int, float)):
            return float(user_data['balance'])
        return None

    def get_user_status(self, username: str, password: str) -> Optional[str]:
        """
        Get user's status from GPT platform.
        
        Args:
            username: GPT platform username
            password: GPT platform password
            
        Returns:
            str: User's status if successful, None otherwise
        """
        user_data = self.get_user_data(username, password)
        return user_data.get('status') if user_data else None
