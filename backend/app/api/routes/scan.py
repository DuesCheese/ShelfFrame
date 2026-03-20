from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import SessionLocal, get_session
from app.schemas import ScanRequest, ScanResult
from app.services.media_roots import bootstrap_media_root, list_media_roots
from app.services.scanner import ScanSummary, scan_library
from app.services.thumbnails import generate_work_thumbnails

router = APIRouter(prefix='/scan', tags=['scan'])


@router.post('', response_model=ScanResult)
def trigger_scan(
    payload: ScanRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> ScanResult:
    bootstrap_media_root(session)

    touched_work_ids: list[int] = []
    if payload.root:
        summary = scan_library(session=session, root=payload.root)
        roots = [str(payload.root.expanduser().resolve())]
        touched_work_ids.extend(summary.touched_work_ids)
        _schedule_thumbnail_generation(background_tasks, touched_work_ids)
        return _to_response(summary, roots)

    roots = [item.path for item in list_media_roots(session) if item.enabled]
    if not roots:
        roots = [str(settings.media_root.expanduser().resolve())]

    combined = ScanSummary()
    for root in roots:
        current = scan_library(session=session, root=root)
        combined.discovered += current.discovered
        combined.created += current.created
        combined.updated += current.updated
        combined.skipped += current.skipped
        combined.touched_work_ids.extend(current.touched_work_ids)

    _schedule_thumbnail_generation(background_tasks, combined.touched_work_ids)
    return _to_response(combined, roots)



def _schedule_thumbnail_generation(background_tasks: BackgroundTasks, work_ids: list[int]) -> None:
    unique_ids = sorted(set(work_ids))
    if unique_ids:
        background_tasks.add_task(_generate_thumbnails_after_scan, unique_ids)



def _generate_thumbnails_after_scan(work_ids: list[int]) -> None:
    with SessionLocal() as session:
        for work_id in work_ids:
            try:
                generate_work_thumbnails(session, work_id)
            except ValueError:
                continue



def _to_response(summary: ScanSummary, roots: list[str]) -> ScanResult:
    return ScanResult(
        discovered=summary.discovered,
        created=summary.created,
        updated=summary.updated,
        skipped=summary.skipped,
        roots=roots,
    )
