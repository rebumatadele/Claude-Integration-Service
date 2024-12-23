# app/schemas/configuration.py

from pydantic import BaseModel, Field
from typing import Optional

class UpdateConfigRequest(BaseModel):
    api_key: Optional[str] = Field(None, description="Claude API key")
    base_url: Optional[str] = Field(None, description="Base URL for Claude API")
    model: Optional[str] = Field(None, description="Model name for Claude API")
    token_limit: Optional[int] = Field(None, description="Token limit per request")  # Added token_limit

class GetConfigResponse(BaseModel):
    api_key: Optional[str] = Field(None, description="Claude API key")
    base_url: Optional[str] = Field(None, description="Base URL for Claude API")
    model: Optional[str] = Field(None, description="Model name for Claude API")
    token_limit: Optional[int] = Field(None, description="Token limit per request")  # Added token_limit
