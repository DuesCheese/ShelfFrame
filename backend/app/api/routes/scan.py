from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_session
from app.schemas import ScanRequest, ScanResult
from app.services.scanner import scan_library

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("", response_model=ScanResult)
def trigger_scan(payload: ScanRequest, session: Session = Depends(get_session)) -> ScanResult:
    root = payload.root or settings.media_root
    summary = scan_library(session=session, root=root)
    return ScanResult(
        discovered=summary.discovered,
        created=summary.created,
        updated=summary.updated,
        skipped=summary.skipped,
    )
