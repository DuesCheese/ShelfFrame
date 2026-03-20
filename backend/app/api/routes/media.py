from __future__ import annotations

from mimetypes import guess_type

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_session
from app.services.media_access import resolve_media_file_path

router = APIRouter(prefix='/media', tags=['media'])


@router.get('/files/{file_id}')
def read_media_file(file_id: int, session: Session = Depends(get_session)) -> FileResponse:
    file_path = resolve_media_file_path(session, file_id)
    media_type, _ = guess_type(file_path.name)
    return FileResponse(path=file_path, media_type=media_type or 'application/octet-stream', filename=file_path.name)
