# worker.py

import asyncio
from app.main import process_queue_task
from loguru import logger

async def main():
    logger.info("Starting background queue processing task.")
    await process_queue_task()

if __name__ == "__main__":
    asyncio.run(main())
