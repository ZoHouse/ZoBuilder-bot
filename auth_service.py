import logging
import asyncio
from typing import Dict, Any, Optional
from zopassport import ZoPassportSDK, MemoryStorageAdapter

from config import ZO_CLIENT_KEY

logger = logging.getLogger(__name__)

class ZoAuthService:
    @classmethod
    async def _get_sdk_instance(cls) -> ZoPassportSDK:
        """Create a fresh SDK instance for the current event loop."""
        if not ZO_CLIENT_KEY:
            logger.error("ZO_CLIENT_KEY not set in environment")
            raise ValueError("ZO_CLIENT_KEY is required")
        
        # Use MemoryStorageAdapter since we don't need persistent session storage
        # for the bot itself (user sessions are managed via Telegram state)
        storage = MemoryStorageAdapter()
        
        sdk = ZoPassportSDK(
            client_key=ZO_CLIENT_KEY,
            storage_adapter=storage,
            debug=True # Enable debug for development
        )
        # Initialize the SDK
        await sdk.initialize()
        logger.info("ZoPassport SDK initialized successfully")
        return sdk

    @classmethod
    async def send_otp(cls, country_code: str, phone_number: str) -> Dict[str, Any]:
        """Send OTP to the specified phone number."""
        sdk = None
        try:
            sdk = await cls._get_sdk_instance()
            # Ensure country code doesn't have + prefix
            country_code = country_code.replace("+", "")
            
            logger.info(f"Sending OTP to {country_code}{phone_number}")
            result = await sdk.auth.send_otp(country_code, phone_number)
            return result
        except Exception as e:
            logger.error(f"Error sending OTP: {e}")
            return {"success": False, "message": str(e)}
        finally:
            if sdk:
                await sdk.close()

    @classmethod
    async def verify_otp(cls, country_code: str, phone_number: str, otp: str) -> Dict[str, Any]:
        """Verify OTP and return auth result."""
        sdk = None
        try:
            sdk = await cls._get_sdk_instance()
            country_code = country_code.replace("+", "")
            
            logger.info(f"Verifying OTP for {country_code}{phone_number}")
            result = await sdk.login_with_phone(country_code, phone_number, otp)
            return result
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return {"success": False, "message": str(e)}
        finally:
            if sdk:
                await sdk.close()
            
    @classmethod
    async def close(cls):
        """Close the SDK connection (deprecated)."""
        pass
