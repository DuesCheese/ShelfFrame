from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import Work, WorkType
from app.schemas import FileRead, SidecarActionResult, TagRead, WorkRead
from app.services.search import apply_work_filters
from app.services.sidecar import export_work_sidecar, import_work_sidecar

router = APIRouter(prefix='/works', tags=['works'])


@router.get('', response_model=list[WorkRead])
def list_works(
    work_type: WorkType | None = Query(default=None, alias='type'),
    tag: str | None = None,
    q: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_session),
) -> list[WorkRead]:
    query = select(Work).options(selectinload(Work.files), selectinload(Work.tags)).order_by(Work.updated_at.desc())
    query = apply_work_filters(query, work_type=work_type, tag=tag, search_term=q)

    works = session.scalars(query).unique().all()
    return [_serialize_work(work) for work in works]


@router.get('/{work_id}', response_model=WorkRead)
def get_work(work_id: int, session: Session = Depends(get_session)) -> WorkRead:
    work = session.scalar(select(Work).options(selectinload(Work.files), selectinload(Work.tags)).where(Work.id == work_id))
    if work is None:
        raise HTTPException(status_code=404, detail='Work not found')
    return _serialize_work(work)


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
        files=[FileRead.model_validate(media_file, from_attributes=True) for media_file in sorted(work.files, key=lambda item: item.order_index)],
    )
