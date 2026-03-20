from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_session
from app.schemas import MediaRootCreate, MediaRootRead, SettingRead
from app.services.media_roots import add_media_root, bootstrap_media_root, delete_media_root, list_media_roots

router = APIRouter(prefix='/settings', tags=['settings'])


@router.get('', response_model=SettingRead)
def get_settings(session: Session = Depends(get_session)) -> SettingRead:
    bootstrap_media_root(session)
    media_roots = list_media_roots(session)
    return SettingRead(
        database_url=settings.database_url,
        media_roots=[MediaRootRead(id=item.id, path=item.path, enabled=item.enabled) for item in media_roots],
    )


@router.post('/media-roots', response_model=MediaRootRead, status_code=status.HTTP_201_CREATED)
def create_media_root(payload: MediaRootCreate, session: Session = Depends(get_session)) -> MediaRootRead:
    media_root = add_media_root(session, payload.path)
    return MediaRootRead(id=media_root.id, path=media_root.path, enabled=media_root.enabled)


@router.delete('/media-roots/{media_root_id}', status_code=status.HTTP_204_NO_CONTENT)
def remove_media_root(media_root_id: int, session: Session = Depends(get_session)) -> Response:
    deleted = delete_media_root(session, media_root_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='Media root not found')
    return Response(status_code=status.HTTP_204_NO_CONTENT)
