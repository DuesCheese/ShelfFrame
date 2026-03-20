from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ShelfFrame API"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./shelfframe.db"
    media_root: Path = Path("./media")

    model_config = SettingsConfigDict(env_prefix="SHELFFRAME_", extra="ignore")


settings = Settings()
