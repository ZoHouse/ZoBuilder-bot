import logging
import asyncio
from typing import Dict, Any, Optional
from zopassport import ZoPassportSDK, MemoryStorageAdapter

from config import ZO_CLIENT_KEY

logger = logging.getLogger(__name__)

class ZoAuthService:
    _instance = None
    _sdk = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ZoAuthService, cls).__new__(cls)
        return cls._instance

    @classmethod
    async def get_sdk(cls) -> ZoPassportSDK:
        """Get or initialize the SDK instance."""
        if cls._sdk is None:
            if not ZO_CLIENT_KEY:
                logger.error("ZO_CLIENT_KEY not set in environment")
                raise ValueError("ZO_CLIENT_KEY is required")
            
            # Use MemoryStorageAdapter since we don't need persistent session storage
            # for the bot itself (user sessions are managed via Telegram state)
            storage = MemoryStorageAdapter()
            
            cls._sdk = ZoPassportSDK(
                client_key=ZO_CLIENT_KEY,
                storage_adapter=storage,
                debug=True # Enable debug for development
            )
            # Initialize the SDK
            await cls._sdk.initialize()
            logger.info("ZoPassport SDK initialized successfully")
            
        return cls._sdk

    @classmethod
    async def send_otp(cls, country_code: str, phone_number: str) -> Dict[str, Any]:
        """Send OTP to the specified phone number."""
        try:
            sdk = await cls.get_sdk()
            # Ensure country code doesn't have + prefix
            country_code = country_code.replace("+", "")
            
            logger.info(f"Sending OTP to {country_code}{phone_number}")
            result = await sdk.auth.send_otp(country_code, phone_number)
            return result
        except Exception as e:
            logger.error(f"Error sending OTP: {e}")
            return {"success": False, "message": str(e)}

    @classmethod
    async def verify_otp(cls, country_code: str, phone_number: str, otp: str) -> Dict[str, Any]:
        """Verify OTP and return auth result."""
        try:
            sdk = await cls.get_sdk()
            country_code = country_code.replace("+", "")
            
            logger.info(f"Verifying OTP for {country_code}{phone_number}")
            result = await sdk.login_with_phone(country_code, phone_number, otp)
            return result
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return {"success": False, "message": str(e)}
            
    @classmethod
    async def close(cls):
        """Close the SDK connection."""
        if cls._sdk:
            await cls._sdk.close()
            cls._sdk = None
