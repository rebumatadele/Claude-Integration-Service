#config
from pydantic import BaseModel, Field
from typing import Any, List, Optional
from loguru import logger
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")  # Ensure this path is correct

class RateLimitConfig(BaseModel):
    max_rpm: int = Field(60, description="Maximum requests per minute")
    max_rph: int = Field(1000, description="Maximum requests per hour")
    cooldown_period: int = Field(30, description="Cooldown period in seconds after rate limit is hit")
    token_limit: int = Field(10000, description="Maximum token usage per request")

class QueueConfig(BaseModel):
    max_queue_size: int = Field(1000, description="Maximum number of chunks in queue")
    persistence_path: str = Field("app/queue.db", description="Path to the SQLite database for persistence")
    chunk_size_limit: int = Field(5000, description="Maximum size of a text chunk")

class RequestConfig(BaseModel):
    max_retries: int = Field(3, description="Maximum number of retry attempts for failed requests")
    timeout: int = Field(30, description="Timeout duration for API requests in seconds")
    backoff_factor: float = Field(1.5, description="Exponential backoff factor for retries")

class CallbackConfig(BaseModel):
    allowed_domains: List[str] = Field(default_factory=list, description="List of allowed callback domains")
    auth_token: Optional[str] = Field(None, description="Authentication token to include in callbacks")

class Settings(BaseModel):
    rate_limit: RateLimitConfig = RateLimitConfig()
    queue: QueueConfig = QueueConfig()
    request: RequestConfig = RequestConfig()
    callback: CallbackConfig = CallbackConfig()
    
    class Config:
        # No need to specify env_file here as dotenv is already loaded
        pass

settings = Settings(
    callback=CallbackConfig(
        allowed_domains=[domain.strip() for domain in os.getenv("ALLOWED_CALLBACK_DOMAINS", "*").split(",") if domain.strip()],
        auth_token=os.getenv("CALLBACK_AUTH_TOKEN")
    )
)
logger.debug(f"Configurations Loaded: {settings.dict(exclude={'callback': {'auth_token'}})}")
