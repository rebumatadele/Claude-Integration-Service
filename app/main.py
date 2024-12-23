# main.py

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import queue, processing, status, configuration
from app.utils.database import init_db
from app.utils.request_handler import request_handler_instance
from app.utils.callback_dispatcher import callback_dispatcher_instance
from app.utils.queue_manager import queue_manager_instance
from loguru import logger
from app.utils.settings_loader import initialize_settings
from sqlalchemy import select
from app.models import Job, JobStatus
from app.utils.database import async_session
from sqlalchemy.orm import selectinload

app = FastAPI(
    title="Claude Integration Module",
    description="API for managing and processing text chunks with Claude.",
    version="1.0.0",
    contact={
        "name": "Rebuma Tadele",
        "url": "https://www.linkedin.com/in/rebumatadele/",
        "email": "rebumatadele4@gmail.com",
    }
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(configuration.router)  # Adds /config/update_config and /config/get_config endpoints
app.include_router(queue.router, prefix="/queue", tags=["Queue Management"])
app.include_router(processing.router, prefix="/process", tags=["Processing"])
app.include_router(status.router, prefix="/status", tags=["Status"])

# Root endpoint - Health Check
@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "OK", "message": "Claude Integration Module is running!"}

# Background task for processing queue and dispatching callbacks
async def process_queue_task():
    while True:
        try:
            # Wait until there's a new item in the queue
            await queue_manager_instance.new_item_event.wait()

            # Clear the event before processing
            queue_manager_instance.new_item_event.clear()

            logger.info("New items detected in the queue. Starting processing.")

            # Process all available items in the queue
            while True:
                result = await request_handler_instance.process_next()
                if "message" in result and result["message"] == "No chunks available for processing.":
                    logger.info("No more chunks to process.")
                    break

            # Check and dispatch callbacks after processing
            await check_and_dispatch_callbacks()
        except Exception as e:
            logger.error(f"Error processing queue: {e}")

        # Optional: Sleep for a short duration to prevent tight looping
        await asyncio.sleep(1)  # Adjust sleep duration as needed

async def check_and_dispatch_callbacks():
    async with async_session() as session:
        # Fetch all jobs with status COMPLETED
        result = await session.execute(
            select(Job)
            .where(Job.status == JobStatus.COMPLETED)
            .options(selectinload(Job.chunks))
        )
        completed_jobs = result.scalars().all()

        for job in completed_jobs:
            # Dispatch callback asynchronously
            asyncio.create_task(callback_dispatcher_instance.dispatch_callback(job.id))

            # Mark the job as CALLBACK_DISPATCHED to prevent re-dispatching
            job.status = JobStatus.CALLBACK_DISPATCHED
        await session.commit()

# Event handler to initialize the database and load settings
@app.on_event("startup")
async def on_startup():
    await init_db()
    await initialize_settings()  # Load initial settings without exiting
    asyncio.create_task(process_queue_task())
    logger.info("Background queue processing and callback dispatching task started.")

# Event handler to close resources on shutdown
@app.on_event("shutdown")
async def on_shutdown():
    await request_handler_instance.close()
    logger.info("Shutdown complete.")
