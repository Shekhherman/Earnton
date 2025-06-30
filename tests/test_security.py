import os
import pytest
import asyncio
from bot import bot, dp
from bonus_system import BonusSystem
from security import SecurityManager

# Configure test settings
TEST_USER_ID = 123456789
TEST_API_TOKEN = "test_api_token_123"

@pytest.fixture
def security_manager():
    """Create a security manager instance for testing."""
    return SecurityManager("test_db.sqlite")

@pytest.fixture
def bonus_system():
    """Create a bonus system instance for testing."""
    return BonusSystem("test_db.sqlite")

async def test_rate_limiting(security_manager):
    """Test rate limiting functionality."""
    # Test exceeding rate limit
    for _ in range(61):
        try:
            await security_manager.get_user_ip({"message": {"effective_chat": {"id": TEST_USER_ID}}})
        except Exception as e:
            assert "Rate limit exceeded" in str(e)
            break
    else:
        pytest.fail("Rate limit not enforced")

async def test_message_validation():
    """Test message validation."""
    # Test long message
    long_message = "a" * 4097
    update = {"message": {"text": long_message}}
    
    try:
        await dp.process_update(update)
        pytest.fail("Long message not detected")
    except Exception as e:
        assert "Message too long" in str(e)

async def test_file_size_validation():
    """Test file size validation."""
    # Test large file
    update = {"message": {"document": {"file_size": 51 * 1024 * 1024 + 1}}}
    
    try:
        await dp.process_update(update)
        pytest.fail("Large file not detected")
    except Exception as e:
        assert "File too large" in str(e)

async def test_bonus_rate_limiting(bonus_system):
    """Test bonus system rate limiting."""
    # Test exceeding bonus check rate limit
    for _ in range(11):
        try:
            await bonus_system.get_daily_bonus(TEST_USER_ID)
        except Exception as e:
            assert "Rate limit exceeded" in str(e)
            break
    else:
        pytest.fail("Bonus check rate limit not enforced")

async def test_bonus_claim_rate_limiting(bonus_system):
    """Test bonus claim rate limiting."""
    # Test exceeding bonus claim rate limit
    for _ in range(6):
        try:
            await bonus_system.claim_daily_bonus(TEST_USER_ID)
        except Exception as e:
            assert "Rate limit exceeded" in str(e)
            break
    else:
        pytest.fail("Bonus claim rate limit not enforced")

async def test_bonus_cooldown(bonus_system):
    """Test bonus cooldown period."""
    # First claim should succeed
    result = await bonus_system.claim_daily_bonus(TEST_USER_ID)
    assert result is True
    
    # Second claim within cooldown should fail
    try:
        await bonus_system.claim_daily_bonus(TEST_USER_ID)
        pytest.fail("Bonus cooldown not enforced")
    except Exception as e:
        assert "Bonus cooldown not reached" in str(e)

async def test_input_validation(security_manager):
    """Test input validation."""
    # Test invalid user ID
    try:
        await security_manager.get_user_ip({"message": {"effective_chat": {"id": "invalid"}}})
        pytest.fail("Invalid user ID not detected")
    except Exception as e:
        assert "Invalid user_id" in str(e)

async def test_error_handling():
    """Test error handling."""
    # Test database error
    try:
        await dp.process_update({"invalid": "data"})
        pytest.fail("Invalid update not detected")
    except Exception as e:
        assert "Error processing update" in str(e)

if __name__ == "__main__":
    pytest.main()
