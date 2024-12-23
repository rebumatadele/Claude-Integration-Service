# routers/status.py

from fastapi import APIRouter, HTTPException
from loguru import logger
from app.utils.response_aggregator import response_aggregator_instance
from app.utils.rate_limiter import rate_limiter_instance
from app.config import settings
from app.utils.settings_loader import settings_loader

router = APIRouter()

@router.get("/final_result/{job_id}", summary="Retrieve combined processed result")
async def get_final_result(job_id: str):
    """
    Retrieves the combined processed result for a specific job.
    """
    try:
        result = await response_aggregator_instance.get_final_result(job_id)
        if result is None:
            raise HTTPException(status_code=404, detail="No results available for the given job_id.")
        return {"final_result": result}
    except Exception as e:
        logger.error(f"Error retrieving final result: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving the final result.")

@router.get("/rate_limits", summary="Get current rate limit status")
async def get_rate_limits():
    """
    Returns the current rate limit configuration and usage.
    """
    return rate_limiter_instance.get_current_limits()

@router.get("/metrics", summary="Get system metrics and performance indicators")
async def get_system_metrics():
    """
    Returns system metrics such as queue size, average response times, and success/failure rates.
    """
    try:
        # Await the asynchronous methods
        queue_length = await response_aggregator_instance.get_queue_length()
        average_response_time = await response_aggregator_instance.get_average_response_time()
        success_rate = await response_aggregator_instance.get_success_rate()

        # Return the metrics
        metrics = {
            "queue_length": queue_length,
            "average_response_time": average_response_time,
            "success_rate": success_rate,
        }
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving system metrics: {e}")

@router.get("/debug", summary="Debug Settings", tags=["Debug"])
async def debug_settings():
    """
    Returns non-sensitive parts of the configuration for debugging purposes.
    Dynamically fetches API-related settings from the database.
    """
    try:
        # Fetch the API configuration from settings_loader
        api_config = await settings_loader.get_api_config()

        # Ensure database values are retrieved dynamically
        return {
            "rate_limit": settings.rate_limit.dict(),
            "queue": settings.queue.dict(),
            "request": settings.request.dict(),
            "api_base_url": api_config.base_url if api_config.base_url else "Not Set",
            "api_key_loaded": bool(api_config.api_key),  # Indicates if API key is loaded
            "token_limit": api_config.token_limit,  # Optional addition for debugging token limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving debug settings: {e}")
