# utils/response_aggregator.py

from typing import Dict, Any, List, Optional
from sqlalchemy import func, select, delete
from app.utils.database import async_session
from app.models import TextChunk, ChunkStatus, Job
import asyncio
from loguru import logger

class ResponseAggregator:
    def __init__(self):
        self.lock = asyncio.Lock()

    async def add_result(self, chunk_id: str, result: str):
        """
        Stores the result of a processed chunk in the database.

        Args:
            chunk_id (str): The ID of the chunk.
            result (str): The processed result.
        """
        async with self.lock:
            async with async_session() as session:
                chunk = await session.get(TextChunk, chunk_id)
                if chunk:
                    chunk.result = result
                    await session.commit()
                    logger.info(f"Stored result for chunk {chunk_id} in the database.")
                else:
                    logger.error(f"Chunk {chunk_id} not found in the database.")

    async def get_final_result(self, job_id: str) -> Optional[str]:
        """
        Concatenates results of all completed chunks under the given job_id.

        Args:
            job_id (str): The ID of the job.

        Returns:
            Optional[str]: The aggregated final result or None if no results.
        """
        async with async_session() as session:
            # Fetch all completed chunks for the job, ordered by creation time
            result = await session.execute(
                select(TextChunk)
                .where(
                    TextChunk.job_id == job_id,
                    TextChunk.status == ChunkStatus.COMPLETED
                )
                .order_by(TextChunk.created_at.asc())
            )
            completed_chunks = result.scalars().all()

            if not completed_chunks:
                logger.warning(f"No completed chunks found for job {job_id}.")
                return None

            # Fetch results directly from the database
            results = [chunk.result for chunk in completed_chunks if chunk.result]

            # Check if any result is missing
            if len(results) != len(completed_chunks):
                logger.warning(f"Some chunks under job {job_id} are missing results.")

            # Concatenate results in the order they were created
            final_result = " ".join(results)
            return final_result

    async def get_chunk_status(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the processing status and result of a specific chunk.

        Args:
            chunk_id (str): The ID of the chunk.

        Returns:
            Optional[Dict[str, Any]]: Status and result of the chunk, or None if not found.
        """
        async with async_session() as session:
            chunk = await session.get(TextChunk, chunk_id)
            if chunk:
                return {
                    "chunk_id": chunk.id,
                    "status": chunk.status.value,
                    "result": chunk.result
                }
            return None

    async def get_queue_length(self) -> int:
        """
        Returns the number of chunks currently in the queue.

        Returns:
            int: Number of queued chunks.
        """
        async with async_session() as session:
            result = await session.execute(
                select(func.count(TextChunk.id)).where(TextChunk.status == ChunkStatus.QUEUED)
            )
            return result.scalar()

    async def get_average_response_time(self) -> float:
        """
        Calculates the average response time for processed chunks.

        Returns:
            float: Average response time in seconds.
        """
        async with async_session() as session:
            result = await session.execute(
                select(func.avg(func.extract('epoch', TextChunk.processing_end_time - TextChunk.processing_start_time)))
                .where(TextChunk.processing_start_time.isnot(None), TextChunk.processing_end_time.isnot(None))
            )
            average = result.scalar()
            return float(average) if average else 0.0

    async def get_success_rate(self) -> float:
        """
        Calculates the success rate of processed chunks.

        Returns:
            float: Success rate percentage.
        """
        async with async_session() as session:
            total_result = await session.execute(select(func.count(TextChunk.id)))
            total_count = total_result.scalar()
            if total_count == 0:
                return 0.0
            success_result = await session.execute(
                select(func.count(TextChunk.id)).where(TextChunk.status == ChunkStatus.COMPLETED)
            )
            success_count = success_result.scalar()
            return (success_count / total_count) * 100 if total_count > 0 else 0.0

    async def purge_old_results(self, retention_period_days: int = 30):
        """
        Purges results older than the specified retention period.

        Args:
            retention_period_days (int): Number of days to retain results.
        """
        async with self.lock:
            async with async_session() as session:
                purge_date = func.now() - func.interval(f'{retention_period_days} days')
                await session.execute(
                    delete(TextChunk)
                    .where(
                        TextChunk.status == ChunkStatus.COMPLETED,
                        TextChunk.updated_at < purge_date
                    )
                )
                await session.commit()
                logger.info(f"Purged completed chunks older than {retention_period_days} days.")

# Instantiate a global ResponseAggregator
response_aggregator_instance = ResponseAggregator()
