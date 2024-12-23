# routers/configuration
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import async_session
from app.models import Configuration
from app.schemas.configuration import UpdateConfigRequest, GetConfigResponse
from app.utils.security import verify_admin_access
from loguru import logger
from app.utils.settings_loader import settings_loader
from sqlalchemy import select
from typing import AsyncGenerator, Optional
from pydantic import BaseModel

router = APIRouter(
    prefix="/config",
    tags=["Configuration"],
    responses={404: {"description": "Not found"}},
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

@router.post(
    "/update_config",
    summary="Update Claude Configuration",
    dependencies=[Depends(verify_admin_access)],
    response_model=dict,
)
async def update_config(
    request: UpdateConfigRequest, db: AsyncSession = Depends(get_db)
):
    """
    Updates or sets the Claude API key, Base URL, Model, and Token Limit in the database.
    Requires the `X-Admin-API-Key` header with the correct token.
    """
    try:
        # Fetch existing configurations
        config_result = await db.execute(select(Configuration))
        configs = config_result.scalars().all()

        # Create a dictionary for easy access
        config_dict = {config.key: config for config in configs}

        # Update or create configurations based on the request
        if request.api_key is not None:
            if "CLAUDE_API_KEY" in config_dict:
                config_dict["CLAUDE_API_KEY"].value = request.api_key
                logger.info("Updating existing CLAUDE_API_KEY in the database.")
            else:
                new_config = Configuration(key="CLAUDE_API_KEY", value=request.api_key)
                db.add(new_config)
                logger.info("Adding new CLAUDE_API_KEY to the database.")

        if request.base_url is not None:
            if "CLAUDE_BASE_URL" in config_dict:
                config_dict["CLAUDE_BASE_URL"].value = request.base_url
                logger.info("Updating existing CLAUDE_BASE_URL in the database.")
            else:
                new_config = Configuration(key="CLAUDE_BASE_URL", value=request.base_url)
                db.add(new_config)
                logger.info("Adding new CLAUDE_BASE_URL to the database.")

        if request.model is not None:
            if "CLAUDE_MODEL" in config_dict:
                config_dict["CLAUDE_MODEL"].value = request.model
                logger.info("Updating existing CLAUDE_MODEL in the database.")
            else:
                new_config = Configuration(key="CLAUDE_MODEL", value=request.model)
                db.add(new_config)
                logger.info("Adding new CLAUDE_MODEL to the database.")

        if request.token_limit is not None:
            if "CLAUDE_TOKEN_LIMIT" in config_dict:
                config_dict["CLAUDE_TOKEN_LIMIT"].value = str(request.token_limit)
                logger.info("Updating existing CLAUDE_TOKEN_LIMIT in the database.")
            else:
                new_config = Configuration(key="CLAUDE_TOKEN_LIMIT", value=str(request.token_limit))
                db.add(new_config)
                logger.info("Adding new CLAUDE_TOKEN_LIMIT to the database.")

        await db.commit()
        logger.info("Configuration updated successfully via configuration endpoint.")

        # Refresh settings in SettingsLoader
        await settings_loader.refresh_api_config()

        return {"message": "Configuration updated successfully."}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/get_config",
    summary="Get Claude Configuration",
    response_model=GetConfigResponse,
    dependencies=[Depends(verify_admin_access)],
)
async def get_config(db: AsyncSession = Depends(get_db)):
    """
    Retrieves the current Claude API key, Base URL, Model, and Token Limit from the database.
    Requires the `X-Admin-API-Key` header with the correct token.
    """
    try:
        config_result = await db.execute(select(Configuration))
        configs = config_result.scalars().all()

        # Initialize with None
        api_key: Optional[str] = None
        base_url: Optional[str] = None
        model: Optional[str] = None
        token_limit: Optional[int] = None

        # Extract configurations
        for config in configs:
            if config.key == "CLAUDE_API_KEY":
                api_key = config.value
            elif config.key == "CLAUDE_BASE_URL":
                base_url = config.value
            elif config.key == "CLAUDE_MODEL":
                model = config.value
            elif config.key == "CLAUDE_TOKEN_LIMIT":
                try:
                    token_limit = int(config.value)
                except ValueError:
                    logger.warning("Invalid CLAUDE_TOKEN_LIMIT value.")

        if api_key is None and base_url is None and model is None and token_limit is None:
            logger.warning("No Claude configurations found in the database.")
            raise HTTPException(
                status_code=404, detail="No Claude configurations found."
            )

        return GetConfigResponse(api_key=api_key, base_url=base_url, model=model, token_limit=token_limit)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
