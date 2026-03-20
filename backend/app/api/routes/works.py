from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import Work
from app.schemas import FileRead, TagRead, WorkRead

router = APIRouter(prefix="/works", tags=["works"])


@router.get("", response_model=list[WorkRead])
def list_works(session: Session = Depends(get_session)) -> list[WorkRead]:
    works = session.scalars(select(Work).options(selectinload(Work.files), selectinload(Work.tags)).order_by(Work.updated_at.desc())).all()
    return [_serialize_work(work) for work in works]


@router.get("/{work_id}", response_model=WorkRead)
def get_work(work_id: int, session: Session = Depends(get_session)) -> WorkRead:
    work = session.scalar(select(Work).options(selectinload(Work.files), selectinload(Work.tags)).where(Work.id == work_id))
    if work is None:
        raise HTTPException(status_code=404, detail="Work not found")
    return _serialize_work(work)


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
