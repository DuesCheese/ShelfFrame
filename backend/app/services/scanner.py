from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import MediaFile, Tag, Work, WorkType
from app.services.sidecar import load_sidecar_for_path

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v'}


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
            image_files = sorted(file for file in entry.rglob('*') if file.suffix.lower() in IMAGE_EXTENSIONS)
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
        .options(selectinload(Work.files), selectinload(Work.tags))
        .where(Work.path == str(entry))
    )
    sidecar_payload = load_sidecar_for_path(entry)

    if work is None:
        work = Work(
            title=(sidecar_payload or {}).get('title') or (entry.stem if entry.is_file() else entry.name),
            path=str(entry),
            type=work_type,
            summary=(sidecar_payload or {}).get('description'),
            cover_path=(sidecar_payload or {}).get('cover_path') or (str(files[0]) if files else None),
        )
        session.add(work)
        session.flush()
        summary.created += 1
    else:
        inferred_title = entry.stem if entry.is_file() else entry.name
        work.title = work.title or inferred_title
        work.type = work_type
        if sidecar_payload and not work.summary:
            work.summary = sidecar_payload.get('description')
        work.cover_path = work.cover_path or (sidecar_payload or {}).get('cover_path') or (str(files[0]) if files else None)
        work.files.clear()
        summary.updated += 1

    _sync_tags_from_sidecar(session, work, sidecar_payload)

    for index, file in enumerate(files):
        media_file = MediaFile(
            work_id=work.id,
            name=file.name,
            path=str(file),
            kind='image' if file.suffix.lower() in IMAGE_EXTENSIONS else 'video',
            size_bytes=file.stat().st_size if file.exists() else None,
            order_index=index,
        )
        work.files.append(media_file)


def _sync_tags_from_sidecar(session: Session, work: Work, sidecar_payload: dict | None) -> None:
    if not sidecar_payload:
        return

    tag_names = sidecar_payload.get('tags') or []
    if not tag_names or work.tags:
        return

    work.tags = [_get_or_create_tag(session, tag_name) for tag_name in tag_names if tag_name.strip()]


def _get_or_create_tag(session: Session, name: str) -> Tag:
    normalized = name.strip()
    tag = session.scalar(select(Tag).where(Tag.name == normalized))
    if tag is None:
        tag = Tag(name=normalized)
        session.add(tag)
        session.flush()
    return tag
