from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import ReadingProgress, Work
from app.schemas import ReadingProgressRead, ReadingProgressUpsert

router = APIRouter(prefix='/progress', tags=['progress'])


@router.get('/{work_id}', response_model=ReadingProgressRead | None)
def get_progress(work_id: int, session: Session = Depends(get_session)) -> ReadingProgressRead | None:
    work = session.query(Work).options(selectinload(Work.progress)).filter(Work.id == work_id).one_or_none()
    if work is None:
        raise HTTPException(status_code=404, detail='Work not found')
    if work.progress is None:
        return None
    return ReadingProgressRead.model_validate(work.progress, from_attributes=True)


@router.put('/{work_id}', response_model=ReadingProgressRead, status_code=status.HTTP_200_OK)
def upsert_progress(
    work_id: int,
    payload: ReadingProgressUpsert,
    session: Session = Depends(get_session),
) -> ReadingProgressRead:
    work = session.query(Work).options(selectinload(Work.files), selectinload(Work.progress)).filter(Work.id == work_id).one_or_none()
    if work is None:
        raise HTTPException(status_code=404, detail='Work not found')

    file_count = len(work.files)
    max_index = max(file_count - 1, 0)
    file_index = min(max(payload.file_index, 0), max_index)
    page = payload.page if payload.page > 0 else file_index + 1
    position = max(0.0, min(payload.position, 1.0))

    progress = work.progress or ReadingProgress(work_id=work_id)
    progress.chapter_key = payload.chapter_key
    progress.file_index = file_index
    progress.page = page
    progress.position = position

    session.add(progress)
    session.commit()
    session.refresh(progress)
    return ReadingProgressRead.model_validate(progress, from_attributes=True)
