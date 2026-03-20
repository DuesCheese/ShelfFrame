from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import MediaFile, Work, WorkType

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v"}


@dataclass
class ScanSummary:
    discovered: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0


def scan_library(session: Session, root: Path) -> ScanSummary:
    summary = ScanSummary()
    root = root.expanduser().resolve()
    if not root.exists():
        return summary

    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            image_files = sorted(file for file in entry.rglob("*") if file.suffix.lower() in IMAGE_EXTENSIONS)
            if not image_files:
                summary.skipped += 1
                continue
            summary.discovered += 1
            _upsert_work(session, entry, WorkType.COMIC, image_files, summary)
            continue

        if entry.suffix.lower() in VIDEO_EXTENSIONS:
            summary.discovered += 1
            _upsert_work(session, entry, WorkType.VIDEO, [entry], summary)
            continue

        summary.skipped += 1

    session.commit()
    return summary


def _upsert_work(session: Session, entry: Path, work_type: WorkType, files: list[Path], summary: ScanSummary) -> None:
    work = session.scalar(
        select(Work)
        .options(selectinload(Work.files))
        .where(Work.path == str(entry))
    )

    if work is None:
        work = Work(
            title=entry.stem if entry.is_file() else entry.name,
            path=str(entry),
            type=work_type,
            cover_path=str(files[0]) if files else None,
        )
        session.add(work)
        session.flush()
        summary.created += 1
    else:
        work.title = entry.stem if entry.is_file() else entry.name
        work.type = work_type
        work.cover_path = str(files[0]) if files else work.cover_path
        work.files.clear()
        summary.updated += 1

    for index, file in enumerate(files):
        media_file = MediaFile(
            work_id=work.id,
            name=file.name,
            path=str(file),
            kind="image" if file.suffix.lower() in IMAGE_EXTENSIONS else "video",
            size_bytes=file.stat().st_size if file.exists() else None,
            order_index=index,
        )
        work.files.append(media_file)
