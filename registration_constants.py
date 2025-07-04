class RegistrationStates:
    """Constants for registration states."""
    AGREEMENT = 0
    USERNAME = 1
    PASSWORD = 2
    GPT_CREDENTIALS = 3
    CONFIRMATION = 4
    COMPLETED = 5

    ALL_STATES = [
        AGREEMENT,
        USERNAME,
        PASSWORD,
        GPT_CREDENTIALS,
        CONFIRMATION,
        COMPLETED
    ]

class RegistrationMessages:
    """Constants for registration messages."""
    WELCOME = "Welcome to the TON Reward Bot!"
    TERMS_OF_SERVICE = "Please read and accept our terms of service:\n\n" \
        "1. You must be at least 18 years old\n" \
        "2. You agree to our privacy policy\n" \
        "3. You understand that TON rewards are subject to market fluctuations\n" \
        "4. You agree not to abuse the system\n\n"
    
    USERNAME_PROMPT = "Please enter your username:\n\n" \
        "Requirements:\n" \
        "• 3-20 characters\n" \
        "• Only letters and numbers\n" \
        "• Must be unique"
    
    PASSWORD_PROMPT = "Please enter your password:\n\n" \
        "Requirements:\n" \
        "• At least 8 characters\n" \
        "• At least one number\n" \
        "• At least one uppercase letter\n" \
        "• At least one lowercase letter\n" \
        "• No common patterns"
    
    GPT_PROMPT = "Please enter your GPT platform credentials:\n\n" \
        "Format: username|password\n\n" \
        "Requirements:\n" \
        "• Username: 3-20 characters\n" \
        "• Password: At least 6 characters\n" \
        "• No common patterns"
    
    CONFIRMATION_PROMPT = "Please confirm your registration:\n\n" \
        "Username: {username}\n" \
        "GPT Username: {gpt_username}\n\n" \
        "Type 'confirm' to complete registration or 'cancel' to start over"
    
    SUCCESS = "Registration completed successfully!\n\n" \
        "You can now use all bot commands.\n" \
        "Type /help to see available commands."
    
    ERROR_INVALID_INPUT = "Invalid input! Please try again."
    ERROR_USERNAME_EXISTS = "Username already exists! Please choose another one."
    ERROR_PASSWORD_WEAK = "Password is too weak! Please make it stronger."
    ERROR_RATE_LIMIT = "Too many attempts. Please wait and try again later."
    ERROR_SYSTEM = "System error occurred. Please try again later."
    
    KEYBOARD = [
        ["Accept", "Decline"],
        ["Confirm", "Cancel"]
    ]

    @classmethod
    def get_confirmation_message(cls, context: dict) -> str:
        """Get confirmation message with user data."""
        return cls.CONFIRMATION_PROMPT.format(
            username=context.get('username', ''),
            gpt_username=context.get('gpt_username', '')
        )
