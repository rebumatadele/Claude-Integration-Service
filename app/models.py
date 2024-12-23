# app/models.py

from sqlalchemy.orm import DeclarativeBase, relationship, selectinload
from sqlalchemy import Column, String, Integer, Text, Enum, DateTime, ForeignKey
from enum import Enum as PyEnum
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class ChunkStatus(PyEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class JobStatus(PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CALLBACK_DISPATCHED = "callback_dispatched"

class Job(Base):
    __tablename__ = 'jobs'

    id = Column(String, primary_key=True, index=True)
    callback_url = Column(String, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Use selectinload for eager loading in async contexts
    chunks = relationship(
        "TextChunk",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy='selectin'  # Eager loading strategy
    )

class TextChunk(Base):
    __tablename__ = 'text_chunks'

    id = Column(String, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    priority = Column(Integer, default=1)
    status = Column(Enum(ChunkStatus), default=ChunkStatus.QUEUED)
    result = Column(Text, nullable=True)  # **New Field Added**
    processing_start_time = Column(DateTime(timezone=True), nullable=True)  # **Optional**
    processing_end_time = Column(DateTime(timezone=True), nullable=True)    # **Optional**
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Foreign key to Job
    job_id = Column(String, ForeignKey('jobs.id'), nullable=True)
    job = relationship("Job", back_populates="chunks", lazy='selectin')  # Eager loading

class Configuration(Base):
    __tablename__ = 'configuration'
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
