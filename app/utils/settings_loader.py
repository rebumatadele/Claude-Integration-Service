#utils/settings_loader
from app.utils.database import async_session
from app.models import Configuration
from sqlalchemy import select
from loguru import logger
from pydantic import BaseModel, Field
from typing import Optional
import asyncio

class APIConfig(BaseModel):
    api_key: Optional[str] = Field(None, description="Claude API key")
    base_url: Optional[str] = Field(None, description="Base URL for Claude API")
    model: Optional[str] = Field(None, description="Model name for Claude API")
    token_limit: Optional[int] = Field(None, description="Token limit per request")  # Added token_limit

class SettingsLoader:
    def __init__(self):
        self.api_config: APIConfig = APIConfig()
        self.lock = asyncio.Lock()
    
    async def load_api_config(self) -> APIConfig:
        async with self.lock:
            async with async_session() as session:
                config_result = await session.execute(select(Configuration))
                configs = config_result.scalars().all()
                
                for config in configs:
                    if config.key == "CLAUDE_API_KEY":
                        self.api_config.api_key = config.value
                    elif config.key == "CLAUDE_BASE_URL":
                        self.api_config.base_url = config.value
                    elif config.key == "CLAUDE_MODEL":
                        self.api_config.model = config.value
                    elif config.key == "CLAUDE_TOKEN_LIMIT":
                        try:
                            self.api_config.token_limit = int(config.value)
                        except ValueError:
                            logger.warning("Invalid CLAUDE_TOKEN_LIMIT value. Using default.")

                # Log warnings if any configuration is missing
                if not self.api_config.api_key:
                    logger.warning("CLAUDE_API_KEY not found or empty in the database.")
                if not self.api_config.base_url:
                    logger.warning("CLAUDE_BASE_URL not found or empty in the database.")
                if not self.api_config.model:
                    logger.warning("CLAUDE_MODEL not found or empty in the database.")
                if not self.api_config.token_limit:
                    logger.warning("CLAUDE_TOKEN_LIMIT not found or empty in the database.")
                
                return self.api_config
    
    async def get_api_config(self) -> APIConfig:
        # If any of the configurations are missing, reload them
        if not self.api_config.api_key or not self.api_config.base_url or not self.api_config.model or not self.api_config.token_limit:
            return await self.load_api_config()
        return self.api_config
    
    async def refresh_api_config(self) -> APIConfig:
        return await self.load_api_config()

# Instantiate a global SettingsLoader
settings_loader = SettingsLoader()

async def initialize_settings():
    await settings_loader.load_api_config()
