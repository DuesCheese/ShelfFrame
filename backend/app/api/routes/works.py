from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import Tag, Work, WorkType
from app.schemas import FileRead, PlaybackEventAck, PlaybackEventCreate, SidecarActionResult, TagRead, VideoPlayerMetadataRead, WorkRead
from app.services.player_metadata import load_video_player_metadata, record_playback_event
from app.services.sidecar import export_work_sidecar, import_work_sidecar
from app.services.thumbnails import generate_work_thumbnails, get_current_cover_thumbnail, set_work_cover

router = APIRouter(prefix='/works', tags=['works'])


@router.get('', response_model=list[WorkRead])
def list_works(
    work_type: WorkType | None = Query(default=None, alias='type'),
    tag: str | None = None,
    q: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_session),
) -> list[WorkRead]:
    query = (
        select(Work)
        .options(selectinload(Work.files), selectinload(Work.tags), selectinload(Work.thumbnails))
        .order_by(Work.updated_at.desc())
    )
    query = select(Work).options(selectinload(Work.files), selectinload(Work.tags), selectinload(Work.progress)).order_by(Work.updated_at.desc())
    if work_type is not None:
        query = query.where(Work.type == work_type)
    if tag:
        query = query.join(Work.tags).where(Tag.name == tag)

    works = session.scalars(query).all()
    return [_serialize_work(session, work) for work in works]


@router.get('/{work_id}', response_model=WorkRead)
def get_work(work_id: int, session: Session = Depends(get_session)) -> WorkRead:
    work = _load_work(session, work_id)
    return _serialize_work(session, work)


@router.get('/{work_id}/player-metadata', response_model=VideoPlayerMetadataRead)
def get_player_metadata(work_id: int, session: Session = Depends(get_session)) -> VideoPlayerMetadataRead:
    work = _load_work(session, work_id)
    if work.type != WorkType.VIDEO:
        raise HTTPException(status_code=400, detail='Player metadata is only available for video works')
    return load_video_player_metadata(session, work)


@router.post('/{work_id}/playback-events', response_model=PlaybackEventAck)
def create_playback_event(work_id: int, payload: PlaybackEventCreate, session: Session = Depends(get_session)) -> PlaybackEventAck:
    work = _load_work(session, work_id)
    if work.type != WorkType.VIDEO:
        raise HTTPException(status_code=400, detail='Playback events are only available for video works')
    record_playback_event(
        session,
        work,
        payload.event_type,
        to_seconds=payload.to_seconds,
        from_seconds=payload.from_seconds,
        duration_seconds=payload.duration_seconds,
    )
    return PlaybackEventAck(work_id=work_id, accepted=True)


@router.get('/{work_id}/cover')
def get_cover_content(work_id: int, session: Session = Depends(get_session)) -> FileResponse:
    work = session.scalar(select(Work).options(selectinload(Work.files)).where(Work.id == work_id))
    if work is None:
        raise HTTPException(status_code=404, detail='Work not found')

    cover_path = work.cover_path or (work.files[0].path if work.files else None)
    if not cover_path:
        raise HTTPException(status_code=404, detail='Cover not found')

    path = Path(cover_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail='Cover file not found')
    return FileResponse(path)


@router.get('/{work_id}/thumbnails/{thumbnail_id}')
def get_thumbnail_content(work_id: int, thumbnail_id: int, session: Session = Depends(get_session)) -> FileResponse:
    thumbnail = session.scalar(select(Thumbnail).where(Thumbnail.id == thumbnail_id, Thumbnail.work_id == work_id))
    if thumbnail is None:
        raise HTTPException(status_code=404, detail='Thumbnail not found')

    path = Path(thumbnail.image_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail='Thumbnail file not found')
    return FileResponse(path)


@router.get('/{work_id}/files/{file_id}/content')
def get_work_file_content(work_id: int, file_id: int, session: Session = Depends(get_session)) -> FileResponse:
    media_file = session.scalar(select(MediaFile).where(MediaFile.id == file_id, MediaFile.work_id == work_id))
    if media_file is None:
        raise HTTPException(status_code=404, detail='File not found')

    file_path = Path(media_file.path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail='File content missing')

    return FileResponse(file_path)


@router.post('/{work_id}/export-sidecar', response_model=SidecarActionResult)
def export_sidecar(work_id: int, session: Session = Depends(get_session)) -> SidecarActionResult:
    try:
        sidecar_path = export_work_sidecar(session, work_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return SidecarActionResult(work_id=work_id, sidecar_path=str(sidecar_path), action='exported')


@router.post('/{work_id}/import-sidecar', response_model=SidecarActionResult)
def import_sidecar(work_id: int, session: Session = Depends(get_session)) -> SidecarActionResult:
    try:
        sidecar_path = import_work_sidecar(session, work_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=f'Sidecar not found: {error.filename or error}') from error

    return SidecarActionResult(work_id=work_id, sidecar_path=str(sidecar_path), action='imported')


def _load_work(session: Session, work_id: int) -> Work:
    work = session.scalar(select(Work).options(selectinload(Work.files), selectinload(Work.tags)).where(Work.id == work_id))
    if work is None:
        raise HTTPException(status_code=404, detail='Work not found')
    return work


def _serialize_work(session: Session, work: Work) -> WorkRead:
    player_metadata = load_video_player_metadata(session, work) if work.type == WorkType.VIDEO else None
    return WorkRead(
        id=work.id,
        title=work.title,
        path=work.path,
        type=work.type,
        summary=work.summary,
        cover_path=work.cover_path,
        cover_url=f'/api/works/{work.id}/cover' if work.cover_path or work.files else None,
        created_at=work.created_at,
        updated_at=work.updated_at,
        tags=[TagRead.model_validate(tag, from_attributes=True) for tag in work.tags],
        files=[FileRead.model_validate(media_file, from_attributes=True) for media_file in sorted(work.files, key=lambda item: item.order_index)],
        player_metadata=player_metadata,
    )
