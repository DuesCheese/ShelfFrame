from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db import get_session
from app.models import ScanTask
from app.schemas import ScanRequest, ScanRunResult, ScanTaskRead
from app.services.media_roots import bootstrap_media_root, list_media_roots
from app.services.scanner import run_scan_task

router = APIRouter(prefix='/scan', tags=['scan'])


@router.post('', response_model=ScanRunResult)
def trigger_scan(payload: ScanRequest, session: Session = Depends(get_session)) -> ScanRunResult:
    bootstrap_media_root(session)

    roots = [str(payload.root.expanduser().resolve())] if payload.root else [item.path for item in list_media_roots(session) if item.enabled]
    if not roots:
        roots = [str(settings.media_root.expanduser().resolve())]

    tasks = [run_scan_task(session=session, root=root) for root in roots]
    return ScanRunResult(
        discovered=sum(task.discovered for task in tasks),
        created=sum(task.created for task in tasks),
        updated=sum(task.updated for task in tasks),
        skipped=sum(task.skipped for task in tasks),
        roots=roots,
        tasks=[_serialize_task(task) for task in tasks],
    )


@router.get('/tasks', response_model=list[ScanTaskRead])
def list_scan_tasks(session: Session = Depends(get_session)) -> list[ScanTaskRead]:
    tasks = session.scalars(select(ScanTask).options(selectinload(ScanTask.logs)).order_by(ScanTask.started_at.desc(), ScanTask.id.desc())).all()
    return [_serialize_task(task) for task in tasks]


@router.get('/tasks/{task_id}', response_model=ScanTaskRead)
def get_scan_task(task_id: int, session: Session = Depends(get_session)) -> ScanTaskRead:
    task = session.scalar(select(ScanTask).options(selectinload(ScanTask.logs)).where(ScanTask.id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail='Scan task not found')
    return _serialize_task(task)


def _serialize_task(task: ScanTask) -> ScanTaskRead:
    return ScanTaskRead.model_validate(task, from_attributes=True)
