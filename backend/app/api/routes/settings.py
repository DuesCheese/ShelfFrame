from fastapi import APIRouter

from app.core.config import settings
from app.schemas import SettingRead

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingRead)
def get_settings() -> SettingRead:
    return SettingRead(database_url=settings.database_url, media_root=settings.media_root)
