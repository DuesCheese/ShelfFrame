from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_session
from app.schemas import ScanRequest, ScanResult
from app.services.media_roots import bootstrap_media_root, list_media_roots
from app.services.scanner import ScanSummary, scan_library

router = APIRouter(prefix='/scan', tags=['scan'])


@router.post('', response_model=ScanResult)
def trigger_scan(payload: ScanRequest, session: Session = Depends(get_session)) -> ScanResult:
    bootstrap_media_root(session)

    if payload.root:
        summary = scan_library(session=session, root=payload.root)
        roots = [str(payload.root.expanduser().resolve())]
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

    return _to_response(combined, roots)


def _to_response(summary: ScanSummary, roots: list[str]) -> ScanResult:
    return ScanResult(
        discovered=summary.discovered,
        created=summary.created,
        updated=summary.updated,
        skipped=summary.skipped,
        roots=roots,
    )
