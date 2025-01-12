# routers/queue
from fastapi import APIRouter, HTTPException, Body, Query, Depends
import httpx
from pydantic import BaseModel, HttpUrl
from app.utils.queue_manager import queue_manager_instance
from typing import List, Optional
from app.schemas.queue import EnqueueMultipleRequest, ChunkItem  # Adjust import based on schema location
from loguru import logger
from app.utils.callback_dispatcher import callback_dispatcher_instance

router = APIRouter()

class EnqueueRequest(BaseModel):
    text: str
    priority: int = 1
async def validate_callback_url(url: HttpUrl) -> bool:
    """
    Validates that the callback URL can accept POST requests by checking its reachability.
    
    Args:
        url (HttpUrl): The callback URL to validate.
    
    Returns:
        bool: True if the URL is valid and reachable, False otherwise.
    """
    url_str = str(url)  # Convert HttpUrl to string
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            # Send a HEAD request first
            response = await client.head(url_str)
            if response.status_code >= 400:
                # Some servers may not support HEAD; fallback to GET
                response = await client.get(url_str)
                if response.status_code >= 400:
                    logger.warning(f"Callback URL {url_str} returned status code {response.status_code}")
                    return False
        return True
    except Exception as e:
        logger.error(f"Error validating callback URL {url_str}: {e}")
        return False

@router.post("/", summary="Enqueue a text chunk for processing")
async def enqueue_chunk(data: EnqueueRequest):
    """
    Enqueue a single text chunk for later processing.
    Returns a unique `chunk_id` that can be used to check processing status.
    """
    try:
        chunk_id = await queue_manager_instance.enqueue(data.text, data.priority)
        logger.info(f"Enqueued chunk: {chunk_id}")
        return {"chunk_id": chunk_id, "status": "queued"}
    except Exception as e:
        logger.error(f"Error enqueuing chunk: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bulk", summary="Enqueue multiple text chunks for processing with a callback URL")
async def enqueue_multiple_chunks(data: EnqueueMultipleRequest):
    """
    Enqueue multiple text chunks for processing.
    Sends the final aggregated result to the specified `callback_url` once processing is complete.
    Returns a `job_id` that can be used to track the job status.
    """
    try:
        # Validate the callback URL
        # is_valid = await validate_callback_url(data.callback_url)
        is_valid = True
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid or unreachable callback URL.")

        # Prepare the list of tuples (text, priority)
        chunks = [(chunk.text, chunk.priority or 1) for chunk in data.chunks]

        # Enqueue multiple chunks under a single job
        job_id = await queue_manager_instance.enqueue_multiple(chunks, data.callback_url)

        logger.info(f"Enqueued multiple chunks under job {job_id}")

        return {"job_id": job_id, "status": "queued"}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error enqueuing multiple chunks: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status", summary="Get current queue status")
async def get_queue_status(limit: int = Query(10, description="Number of items to list")):
    """
    Returns the current status of the queue, including how many items
    are queued and a sample of queued items.
    """
    try:
        status = await queue_manager_instance.get_status(limit=limit)  # Awaited
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
