from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import Tag, Work, WorkType
from app.schemas import FileRead, PlaybackEventAck, PlaybackEventCreate, SidecarActionResult, TagRead, VideoPlayerMetadataRead, WorkRead
from app.services.player_metadata import load_video_player_metadata, record_playback_event
from app.services.sidecar import export_work_sidecar, import_work_sidecar

router = APIRouter(prefix='/works', tags=['works'])


@router.get('', response_model=list[WorkRead])
def list_works(
    work_type: WorkType | None = Query(default=None, alias='type'),
    tag: str | None = None,
    session: Session = Depends(get_session),
) -> list[WorkRead]:
    query = select(Work).options(selectinload(Work.files), selectinload(Work.tags)).order_by(Work.updated_at.desc())
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
        created_at=work.created_at,
        updated_at=work.updated_at,
        tags=[TagRead.model_validate(tag, from_attributes=True) for tag in work.tags],
        files=[FileRead.model_validate(media_file, from_attributes=True) for media_file in sorted(work.files, key=lambda item: item.order_index)],
        player_metadata=player_metadata,
    )
