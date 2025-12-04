"""
Authentication middleware for API endpoints.
Uses a shared secret (API key) for internal service-to-service communication.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from .config import config

# Define the header name for the API key
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    Verify that the provided API key matches the configured secret.

    Args:
        api_key: The API key from the request header

    Returns:
        The validated API key

    Raises:
        HTTPException: If the API key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Include 'X-API-Key' header in your request.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != config.api_secret_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
