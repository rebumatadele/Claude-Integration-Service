# utils/database
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base
import os
from dotenv import load_dotenv

load_dotenv(".env")  # Ensure this path is correct

# Fetch database path from environment variables
QUEUE_DB_PATH = os.getenv("QUEUE_DB_PATH", "app/queue.db")

# Initialize Async Engine and Session
engine: AsyncEngine = create_async_engine(
    f"sqlite+aiosqlite:///{QUEUE_DB_PATH}",
    echo=True,  # Set to False in production
    future=True
)

async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
