# routers/processing
from fastapi import APIRouter, HTTPException, Path
from app.utils.request_handler import request_handler_instance

router = APIRouter()

@router.post("/", summary="Process the next item in the queue")
async def process_next_item():
    """
    Trigger the processing of the next available item in the queue.
    This is an optional manual trigger; in a production environment,
    you might have a background task automatically processing items.
    """
    try:
        result = await request_handler_instance.process_next()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{chunk_id}/status", summary="Get processing status of a specific chunk")
async def get_processing_status(chunk_id: str = Path(..., description="The chunk_id to check")):
    """
    Check the processing status of a given chunk by its unique chunk_id.
    Returns whether it's in queue, in progress, completed, or failed.
    """
    try:
        status = await request_handler_instance.get_completion_status(chunk_id)
        if not status:
            raise HTTPException(status_code=404, detail="Chunk not found")
        return status
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
