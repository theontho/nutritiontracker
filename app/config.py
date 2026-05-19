from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    db_path: Path = Path("data/nutrition.db")
    default_user_id: int = 1
    api_version: str = "0.1.0"

    model_config = {"env_prefix": "NT_"}


settings = Settings()
