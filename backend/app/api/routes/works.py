from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import MediaFile, Tag, Work, WorkType
from app.schemas import FileRead, ReadingProgressRead, SidecarActionResult, TagRead, WorkRead
from app.services.sidecar import export_work_sidecar, import_work_sidecar

router = APIRouter(prefix='/works', tags=['works'])


@router.get('', response_model=list[WorkRead])
def list_works(
    work_type: WorkType | None = Query(default=None, alias='type'),
    tag: str | None = None,
    session: Session = Depends(get_session),
) -> list[WorkRead]:
    query = select(Work).options(selectinload(Work.files), selectinload(Work.tags), selectinload(Work.progress)).order_by(Work.updated_at.desc())
    if work_type is not None:
        query = query.where(Work.type == work_type)
    if tag:
        query = query.join(Work.tags).where(Tag.name == tag)

    works = session.scalars(query).all()
    return [_serialize_work(work) for work in works]


@router.get('/{work_id}', response_model=WorkRead)
def get_work(work_id: int, session: Session = Depends(get_session)) -> WorkRead:
    work = session.scalar(select(Work).options(selectinload(Work.files), selectinload(Work.tags), selectinload(Work.progress)).where(Work.id == work_id))
    if work is None:
        raise HTTPException(status_code=404, detail='Work not found')
    return _serialize_work(work)




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


def _serialize_work(work: Work) -> WorkRead:
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
        files=[_serialize_file(work.id, media_file) for media_file in sorted(work.files, key=lambda item: item.order_index)],
        progress=ReadingProgressRead.model_validate(work.progress, from_attributes=True) if work.progress else None,
    )


def _serialize_file(work_id: int, media_file: MediaFile) -> FileRead:
    return FileRead(
        id=media_file.id,
        name=media_file.name,
        path=media_file.path,
        kind=media_file.kind,
        size_bytes=media_file.size_bytes,
        order_index=media_file.order_index,
        content_url=f'/api/works/{work_id}/files/{media_file.id}/content',
    )
