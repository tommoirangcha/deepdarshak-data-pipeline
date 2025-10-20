from fastapi import Header, HTTPException, status, Depends
from .config import get_settings


def api_key_header(x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> str:
    # Accept either X-API-Key or Authorization: Bearer <key>
    if x_api_key:
        return x_api_key.strip()
    if authorization:
        auth = authorization.strip()
        # Support both 'Bearer <token>' and raw token in Authorization header
        if auth.lower().startswith("bearer "):
            return auth.split(" ", 1)[1].strip()
        return auth
    return ""


def require_api_key(key: str = Depends(api_key_header)) -> None:
    settings = get_settings()
    expected = (settings.api_key or "").strip()
    # If API key is not configured, deny by default for safety
    if not expected:
        # If no API_KEY is configured, deny by default for safety
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API not configured")
    if not key or key.strip() != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return None