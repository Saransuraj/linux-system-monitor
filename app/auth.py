"""
Simple API key authentication.

This is intentionally minimal (a shared secret in a header) rather than
full OAuth/JWT, because the target use case is a single trusted operator
or an internal dashboard talking to this API. If you expose this API
beyond a trusted network, put it behind a proper auth layer / reverse
proxy with TLS.
"""
from fastapi import Header, HTTPException, status

from app.config import settings


async def require_api_key(x_api_key: str = Header(default=None)) -> None:
    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Set the 'X-API-Key' header.",
        )
