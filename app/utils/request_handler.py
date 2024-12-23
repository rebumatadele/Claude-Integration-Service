# utils/request_handler.py

import httpx
import asyncio

from sqlalchemy import func
from app.utils.rate_limiter import rate_limiter_instance
from app.utils.queue_manager import queue_manager_instance
from app.utils.response_aggregator import response_aggregator_instance
from typing import Any, Dict, Optional
from loguru import logger
from app.models import ChunkStatus
from app.utils.settings_loader import settings_loader, APIConfig
from app.utils.database import async_session

class RequestHandler:
    def __init__(self):
        self.max_retries = 3
        self.timeout = 30
        self.backoff_factor = 1.5

    async def process_next(self) -> Dict[str, Any]:
        chunk = await queue_manager_instance.get_next_chunk()
        if chunk:
            async with async_session() as session:
                chunk.processing_start_time = func.now()
                await session.commit()

        if not chunk:
            logger.info("No chunks available for processing.")
            return {"message": "No chunks available for processing."}
        
        attempt = 0
        while attempt < self.max_retries:
            try:
                await rate_limiter_instance.acquire()
                api_config = await settings_loader.get_api_config()
                if not api_config.api_key or not api_config.base_url or not api_config.model:
                    logger.error("Claude configurations are not fully set. Skipping processing.")
                    await queue_manager_instance.update_status(chunk.id, ChunkStatus.FAILED)
                    return {"chunk_id": chunk.id, "status": "failed", "error": "Claude configurations are not fully set."}

                headers = {
                    "x-api-key": api_config.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                }

                json_data = {
                    "model": api_config.model,
                    "messages": [{"role": "user", "content": chunk.text}],
                    "max_tokens": getattr(api_config, 'token_limit', 1024),
                }

                logger.debug(f"Using API Config: {api_config}")
                logger.debug(f"Request payload: {json_data}")

                async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
                    response = await client.post(api_config.base_url, json=json_data)

                rate_limiter_instance.update_from_headers(response.headers)

                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Raw response content: {response.text}")

                if response.status_code == 429:
                    logger.warning("Rate limit exceeded. Retrying with backoff.")
                    await asyncio.sleep(self.backoff_factor ** attempt)
                    attempt += 1
                    continue
                elif response.status_code >= 500:
                    logger.warning(f"Server error ({response.status_code}). Retrying with backoff.")
                    await asyncio.sleep(self.backoff_factor ** attempt)
                    attempt += 1
                    continue
                elif response.status_code != 200:
                    error_message = response.json().get('error', {}).get('message', 'Unknown error')
                    logger.error(f"Anthropic API error ({response.status_code}): {error_message}")
                    await queue_manager_instance.update_status(chunk.id, ChunkStatus.FAILED)
                    return {"chunk_id": chunk.id, "status": "failed", "error": error_message}

                data = response.json()
                content = data.get("content", "")
                if isinstance(content, list):
                    result = "".join([item.get("text", "") for item in content if "text" in item])
                else:
                    result = content

                # **Store the result in the database via ResponseAggregator**
                await response_aggregator_instance.add_result(chunk.id, result)
                async with async_session() as session:
                    chunk.processing_end_time = func.now()
                    await session.commit()
                await queue_manager_instance.update_status(chunk.id, ChunkStatus.COMPLETED)
                logger.info(f"Chunk {chunk.id} processed successfully.")
                return {"chunk_id": chunk.id, "status": "completed", "result": result}

            except httpx.RequestError as e:
                logger.error(f"Request error: {e}. Retrying with backoff.")
                await asyncio.sleep(self.backoff_factor ** attempt)
                attempt += 1
            except Exception as e:
                logger.error(f"Processing error: {e}.")
                logger.debug(f"Chunk ID: {chunk.id}, Attempt: {attempt}")
                await queue_manager_instance.update_status(chunk.id, ChunkStatus.FAILED)
                async with async_session() as session:
                    chunk.processing_end_time = func.now()
                    await session.commit()
                return {"chunk_id": chunk.id, "status": "failed", "error": str(e)}
        async with async_session() as session:
                    chunk.processing_end_time = func.now()
                    await session.commit()
        logger.error(f"Failed to process chunk {chunk.id} after {self.max_retries} attempts.")
        await queue_manager_instance.update_status(chunk.id, ChunkStatus.FAILED)
        return {"chunk_id": chunk.id, "status": "failed", "error": "Max retries exceeded"}

        
    async def get_completion_status(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        return await response_aggregator_instance.get_chunk_status(chunk_id)

    async def close(self):
        # No persistent client to close in this setup
        pass

# Instantiate a global RequestHandler
request_handler_instance = RequestHandler()
