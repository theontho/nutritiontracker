from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_path: Path = Path("data/nutrition.db")
    default_user_id: int = 1
    multi_user_enabled: bool = False
    api_version: str = "0.1.0"
    bearer_token: Optional[str] = None
    local_bearer_token: Optional[str] = None

    model_config = {"env_prefix": "NT_"}

    @model_validator(mode="after")
    def _validate_tokens(self) -> "Settings":
        if self.multi_user_enabled and not self.bearer_token:
            raise ValueError(
                "NT_MULTI_USER_ENABLED requires NT_BEARER_TOKEN. Without a token "
                "every request is unauthenticated, so the combination would hand "
                "user provisioning and token rotation to anonymous callers."
            )
        if self.local_bearer_token and not self.bearer_token:
            raise ValueError(
                "NT_LOCAL_BEARER_TOKEN requires NT_BEARER_TOKEN so non-loopback "
                "requests cannot fall through to unauthenticated access."
            )
        if (
            self.local_bearer_token
            and self.bearer_token
            and self.local_bearer_token == self.bearer_token
        ):
            raise ValueError(
                "NT_LOCAL_BEARER_TOKEN must differ from NT_BEARER_TOKEN so the "
                "loopback credential cannot inherit admin access."
            )
        return self


settings = Settings()
