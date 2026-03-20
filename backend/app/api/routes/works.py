from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import Tag, Work, WorkType
from app.schemas import FileRead, SidecarActionResult, TagRead, WorkRead
from app.services.sidecar import SidecarParseError, export_work_sidecar, import_work_sidecar

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

    works = session.scalars(query).unique().all()
    return [_serialize_work(work) for work in works]


@router.get('/{work_id}', response_model=WorkRead)
def get_work(work_id: int, session: Session = Depends(get_session)) -> WorkRead:
    work = session.scalar(
        select(Work)
        .options(selectinload(Work.files), selectinload(Work.tags), selectinload(Work.thumbnails))
        .where(Work.id == work_id)
    )
    if work is None:
        raise HTTPException(status_code=404, detail='Work not found')
    return _serialize_work(work)


@router.post('/{work_id}/generate-thumbnails', response_model=ThumbnailGenerationResult)
def generate_thumbnails(work_id: int, force: bool = Query(default=False), session: Session = Depends(get_session)) -> ThumbnailGenerationResult:
    try:
        thumbnails = generate_work_thumbnails(session, work_id, force=force)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return ThumbnailGenerationResult(work_id=work_id, generated=len(thumbnails), action='generated')


@router.post('/{work_id}/cover', response_model=WorkRead)
def select_cover(work_id: int, payload: CoverSelectRequest, session: Session = Depends(get_session)) -> WorkRead:
    try:
        work = set_work_cover(session, work_id, payload.thumbnail_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    work = session.scalar(
        select(Work)
        .options(selectinload(Work.files), selectinload(Work.tags), selectinload(Work.thumbnails))
        .where(Work.id == work.id)
    )
    work = session.scalar(select(Work).options(selectinload(Work.files), selectinload(Work.tags), selectinload(Work.progress)).where(Work.id == work_id))
    if work is None:
        raise HTTPException(status_code=404, detail='Work not found')
    return _serialize_work(work)


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
    except SidecarParseError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return SidecarActionResult(work_id=work_id, sidecar_path=str(sidecar_path), action='imported')



def _serialize_work(work: Work) -> WorkRead:
    thumbnails = [
        ThumbnailRead(
            id=thumbnail.id,
            type=thumbnail.type,
            source_path=thumbnail.source_path,
            image_path=thumbnail.image_path,
            ts_sec=thumbnail.ts_sec,
            sort_no=thumbnail.sort_no,
            thumbnail_url=f'/api/works/{work.id}/thumbnails/{thumbnail.id}',
        )
        for thumbnail in sorted(work.thumbnails, key=lambda item: item.sort_no)
    ]
    current_cover = get_current_cover_thumbnail(work)
    current_cover_read = None
    if current_cover is not None:
        current_cover_read = ThumbnailRead(
            id=current_cover.id,
            type=current_cover.type,
            source_path=current_cover.source_path,
            image_path=current_cover.image_path,
            ts_sec=current_cover.ts_sec,
            sort_no=current_cover.sort_no,
            thumbnail_url=f'/api/works/{work.id}/thumbnails/{current_cover.id}',
        )

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
        thumbnails=thumbnails,
        current_cover=current_cover_read,
    )
