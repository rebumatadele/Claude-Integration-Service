# utils/queue_manager.py

import asyncio
from typing import Optional, List, Tuple
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from app.utils.database import async_session
from app.models import TextChunk, Job, JobStatus, ChunkStatus
from app.config import settings
import asyncio
from loguru import logger
import uuid

class QueueManager:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.new_item_event = asyncio.Event()  # Event to signal new items

    async def enqueue(self, text: str, priority: int = 1, job_id: Optional[str] = None) -> str:
        async with self.lock:
            async with async_session() as session:
                # Check queue size
                total = await session.execute(select(func.count(TextChunk.id)))
                total_count = total.scalar()
                if total_count >= settings.queue.max_queue_size:
                    raise Exception("Queue is full")

                # Create a new TextChunk
                chunk_id = str(uuid.uuid4())
                new_chunk = TextChunk(
                    id=chunk_id,
                    text=text,
                    priority=priority,
                    status=ChunkStatus.QUEUED,
                    job_id=job_id
                )
                session.add(new_chunk)
                await session.commit()

                # Signal that a new item has been enqueued
                self.new_item_event.set()

                logger.info(f"Enqueued new chunk: {chunk_id}")
                return chunk_id

    async def enqueue_multiple(self, chunks: List[Tuple[str, int]], callback_url: str) -> str:
        async with self.lock:
            async with async_session() as session:
                # Check if adding these chunks would exceed max_queue_size
                total = await session.execute(select(func.count(TextChunk.id)))
                total_count = total.scalar()
                if total_count + len(chunks) > settings.queue.max_queue_size:
                    raise Exception("Enqueueing these chunks would exceed the maximum queue size.")

                # Create a new Job
                job_id = str(uuid.uuid4())
                new_job = Job(
                    id=job_id,
                    callback_url=str(callback_url),
                    status=JobStatus.PENDING
                )
                session.add(new_job)

                # Create TextChunk instances
                new_chunks = [
                    TextChunk(
                        id=str(uuid.uuid4()),
                        text=chunk_text,
                        priority=priority,
                        status=ChunkStatus.QUEUED,
                        job_id=job_id
                    )
                    for chunk_text, priority in chunks
                ]

                session.add_all(new_chunks)
                await session.commit()

                # Signal that new items have been enqueued
                self.new_item_event.set()

                logger.info(f"Enqueued multiple chunks under job {job_id}")
                return job_id

    async def get_next_chunk(self) -> Optional[TextChunk]:
        async with self.lock:
            async with async_session() as session:
                # Fetch the highest priority queued chunk
                result = await session.execute(
                    select(TextChunk)
                    .where(TextChunk.status == ChunkStatus.QUEUED)
                    .order_by(TextChunk.priority.desc(), TextChunk.created_at.asc())
                    .limit(1)
                )
                chunk = result.scalar_one_or_none()
                if chunk:
                    # Update status to IN_PROGRESS
                    chunk.status = ChunkStatus.IN_PROGRESS
                    # Also, update associated Job status to IN_PROGRESS if not already
                    if chunk.job and chunk.job.status == JobStatus.PENDING:
                        chunk.job.status = JobStatus.IN_PROGRESS
                    await session.commit()
                    logger.info(f"Processing chunk: {chunk.id}")
                return chunk

    async def update_status(self, chunk_id: str, status: ChunkStatus):
        async with self.lock:
            async with async_session() as session:
                # Update the status of the specific TextChunk
                await session.execute(
                    update(TextChunk)
                    .where(TextChunk.id == chunk_id)
                    .values(status=status)
                )

                # Optionally, update processing timestamps
                if status == ChunkStatus.IN_PROGRESS:
                    chunk = await session.get(TextChunk, chunk_id)
                    if chunk:
                        chunk.processing_start_time = func.now()
                elif status in [ChunkStatus.COMPLETED, ChunkStatus.FAILED]:
                    chunk = await session.get(TextChunk, chunk_id)
                    if chunk:
                        chunk.processing_end_time = func.now()

                # Retrieve the chunk along with its associated job
                chunk = await session.get(TextChunk, chunk_id, options=[selectinload(TextChunk.job)])
                if chunk and chunk.job:
                    job = chunk.job

                    # Asynchronously count the total number of chunks for this job
                    result = await session.execute(
                        select(func.count(TextChunk.id)).where(TextChunk.job_id == job.id)
                    )
                    total_chunks = result.scalar()

                    # Count the number of completed chunks
                    result = await session.execute(
                        select(func.count(TextChunk.id)).where(
                            TextChunk.job_id == job.id,
                            TextChunk.status == ChunkStatus.COMPLETED
                        )
                    )
                    completed_count = result.scalar()

                    # Count the number of chunks that are either completed or failed
                    result = await session.execute(
                        select(func.count(TextChunk.id)).where(
                            TextChunk.job_id == job.id,
                            TextChunk.status.in_([ChunkStatus.COMPLETED, ChunkStatus.FAILED])
                        )
                    )
                    total_completed_failed = result.scalar()

                    # Determine if all chunks have been processed
                    if total_completed_failed == total_chunks:
                        if completed_count == total_chunks:
                            job.status = JobStatus.COMPLETED
                        else:
                            job.status = JobStatus.FAILED

                await session.commit()
                logger.info(f"Updated status for chunk {chunk_id} to {status.value}")

    async def get_status(self, limit: int = 10) -> dict:
        async with async_session() as session:
            result = await session.execute(
                select(TextChunk).order_by(TextChunk.created_at.desc()).limit(limit)
            )
            chunks = result.scalars().all()
            return {
                "total_queued": await self._count_status(ChunkStatus.QUEUED),
                "total_in_progress": await self._count_status(ChunkStatus.IN_PROGRESS),
                "total_completed": await self._count_status(ChunkStatus.COMPLETED),
                "total_failed": await self._count_status(ChunkStatus.FAILED),
                "recent_chunks": [
                    {
                        "id": chunk.id,
                        "status": chunk.status.value,
                        "priority": chunk.priority,
                        "created_at": chunk.created_at,
                        "updated_at": chunk.updated_at,
                        "job_id": chunk.job_id
                    } for chunk in chunks
                ]
            }

    async def _count_status(self, status: ChunkStatus) -> int:
        async with async_session() as session:
            result = await session.execute(
                select(func.count(TextChunk.id)).where(TextChunk.status == status)
            )
            return result.scalar()

# Instantiate a global QueueManager
queue_manager_instance = QueueManager()
