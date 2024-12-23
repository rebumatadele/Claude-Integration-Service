# app/schemas/queue
from pydantic import BaseModel, Field, HttpUrl, validator
from typing import List, Optional

class ChunkItem(BaseModel):
    text: str = Field(..., description="Text content of the chunk to be processed.")
    priority: Optional[int] = Field(1, description="Priority of the chunk. Higher numbers indicate higher priority.")

class EnqueueMultipleRequest(BaseModel):
    chunks: List[ChunkItem] = Field(
        ...,
        description="List of chunks to enqueue."
    )
    callback_url: HttpUrl = Field(
        ...,
        description="URL to send the final aggregated result once processing is complete."
    )

    @validator('chunks')
    def validate_chunks(cls, v):
        if not v:
            raise ValueError("Chunks list cannot be empty.")
        return v
