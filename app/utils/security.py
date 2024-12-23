# app/utils/security.py

from fastapi import Header, HTTPException, status
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")  # Ensure this path is correct

# Fetch the admin API access key from the environment variables
ADMIN_API_ACCESS_KEY = os.getenv("ADMIN_API_ACCESS_KEY")

if not ADMIN_API_ACCESS_KEY:
    raise EnvironmentError("ADMIN_API_ACCESS_KEY not found in environment. Please set it in the .env file.")

def verify_admin_access(x_admin_api_key: str = Header(..., alias="X-Admin-API-Key")):
    """
    Verifies the `X-Admin-API-Key` header for admin-level access.

    This function ensures that only requests with the correct admin API key
    can access sensitive admin endpoints.
    """
    if x_admin_api_key != ADMIN_API_ACCESS_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API access key.",
            headers={"WWW-Authenticate": "API key"},
        )
