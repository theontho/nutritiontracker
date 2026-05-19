from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer(auto_error=False)


def require_auth(credentials: HTTPAuthorizationCredentials | None = Security(_bearer)) -> None:
    """Validate Bearer token if NT_BEARER_TOKEN is configured. Pass-through when not set."""
    if not settings.bearer_token:
        return
    if credentials is None or credentials.credentials != settings.bearer_token:
        raise HTTPException(status_code=401, detail="Invalid or missing Bearer token")
