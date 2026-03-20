from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import MediaFile, ScanLog, ScanLogLevel, ScanTask, ScanTaskStatus, Tag, Work, WorkType
from app.services.sidecar import SidecarParseError, load_sidecar_for_path

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v'}


class ScanErrorCode(str, Enum):
    ROOT_NOT_FOUND = 'root_not_found'
    PERMISSION_DENIED = 'permission_denied'
    SIDECAR_PARSE_FAILED = 'sidecar_parse_failed'
    FILE_CORRUPTED = 'file_corrupted'
    FILE_STAT_FAILED = 'file_stat_failed'
    DIRECTORY_LIST_FAILED = 'directory_list_failed'


@dataclass
class ScanSummary:
    discovered: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    error_count: int = 0


class ScanRecorder:
    def __init__(self, session: Session, task: ScanTask):
        self.session = session
        self.task = task

    def info(self, message: str, path: Path | str | None = None, code: ScanErrorCode | None = None) -> None:
        self._append(ScanLogLevel.INFO, message, path, code)

    def warning(self, message: str, path: Path | str | None = None, code: ScanErrorCode | None = None) -> None:
        self._append(ScanLogLevel.WARNING, message, path, code)

    def error(self, message: str, path: Path | str | None = None, code: ScanErrorCode | None = None) -> None:
        self._append(ScanLogLevel.ERROR, message, path, code)

    def _append(self, level: ScanLogLevel, message: str, path: Path | str | None, code: ScanErrorCode | None) -> None:
        log = ScanLog(
            task_id=self.task.id,
            level=level,
            code=code.value if code else None,
            path=str(path) if path is not None else None,
            message=message,
        )
        self.session.add(log)
        if level == ScanLogLevel.ERROR:
            self.task.error_message = message
        self.session.flush()


def run_scan_task(session: Session, root: Path | str) -> ScanTask:
    resolved_root = Path(root).expanduser().resolve()
    task = ScanTask(root_path=str(resolved_root), status=ScanTaskStatus.RUNNING)
    session.add(task)
    session.flush()

    recorder = ScanRecorder(session, task)
    recorder.info('Scan started', path=resolved_root)

    try:
        summary = scan_library(session=session, root=resolved_root, recorder=recorder)
    except Exception as error:
        task.status = ScanTaskStatus.FAILED
        task.finished_at = datetime.now(timezone.utc)
        task.error_message = str(error)
        recorder.error(f'Scan failed: {error}', path=resolved_root)
        session.commit()
        raise

    task.discovered = summary.discovered
    task.created = summary.created
    task.updated = summary.updated
    task.skipped = summary.skipped
    task.finished_at = datetime.now(timezone.utc)
    task.status = ScanTaskStatus.COMPLETED_WITH_ERRORS if summary.error_count else ScanTaskStatus.SUCCEEDED
    if summary.error_count == 0:
        task.error_message = None
    recorder.info(
        f'Scan finished with discovered={summary.discovered}, created={summary.created}, updated={summary.updated}, skipped={summary.skipped}',
        path=resolved_root,
    )
    session.commit()
    session.refresh(task)
    return task


def scan_library(session: Session, root: Path, recorder: ScanRecorder | None = None) -> ScanSummary:
    summary = ScanSummary()
    root = root.expanduser().resolve()

    if not root.exists():
        summary.error_count += 1
        if recorder:
            recorder.error('Scan root does not exist', path=root, code=ScanErrorCode.ROOT_NOT_FOUND)
        return summary

    if not root.is_dir():
        summary.error_count += 1
        if recorder:
            recorder.error('Scan root is not a directory', path=root, code=ScanErrorCode.ROOT_NOT_FOUND)
        return summary

    try:
        entries = sorted(root.iterdir())
    except PermissionError:
        summary.error_count += 1
        if recorder:
            recorder.error('Permission denied while listing scan root', path=root, code=ScanErrorCode.PERMISSION_DENIED)
        return summary
    except OSError as error:
        summary.error_count += 1
        if recorder:
            recorder.error(f'Failed to list scan root: {error}', path=root, code=ScanErrorCode.DIRECTORY_LIST_FAILED)
        return summary

    for entry in entries:
        try:
            if entry.is_dir():
                sidecar_payload = _load_sidecar_payload(entry, summary, recorder)
                image_files = _discover_image_files(entry, recorder, summary)
                if not image_files:
                    summary.skipped += 1
                    continue
                summary.discovered += 1
                _upsert_work(session, entry, WorkType.COMIC, image_files, summary, recorder, sidecar_payload)
                continue

            if entry.suffix.lower() in VIDEO_EXTENSIONS:
                summary.discovered += 1
                _upsert_work(session, entry, WorkType.VIDEO, [entry], summary, recorder)
                continue

            summary.skipped += 1
        except PermissionError:
            summary.error_count += 1
            summary.skipped += 1
            if recorder:
                recorder.error('Permission denied while scanning entry', path=entry, code=ScanErrorCode.PERMISSION_DENIED)
        except OSError as error:
            summary.error_count += 1
            summary.skipped += 1
            if recorder:
                recorder.error(f'Failed to scan entry: {error}', path=entry, code=ScanErrorCode.FILE_CORRUPTED)

    session.flush()
    return summary


def _load_sidecar_payload(entry: Path, summary: ScanSummary, recorder: ScanRecorder | None) -> dict | None:
    try:
        return load_sidecar_for_path(entry)
    except SidecarParseError as error:
        summary.error_count += 1
        if recorder:
            recorder.error(str(error), path=error.sidecar_path, code=ScanErrorCode.SIDECAR_PARSE_FAILED)
        return None


def _discover_image_files(entry: Path, recorder: ScanRecorder | None, summary: ScanSummary) -> list[Path]:
    files: list[Path] = []
    try:
        candidates = sorted(entry.rglob('*'))
    except PermissionError:
        summary.error_count += 1
        if recorder:
            recorder.error('Permission denied while traversing directory', path=entry, code=ScanErrorCode.PERMISSION_DENIED)
        return files
    except OSError as error:
        summary.error_count += 1
        if recorder:
            recorder.error(f'Failed to traverse directory: {error}', path=entry, code=ScanErrorCode.DIRECTORY_LIST_FAILED)
        return files

    for file in candidates:
        if file.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        try:
            size = file.stat().st_size
        except PermissionError:
            summary.error_count += 1
            if recorder:
                recorder.error('Permission denied while reading file metadata', path=file, code=ScanErrorCode.PERMISSION_DENIED)
            continue
        except OSError as error:
            summary.error_count += 1
            if recorder:
                recorder.error(f'Failed to read file metadata: {error}', path=file, code=ScanErrorCode.FILE_STAT_FAILED)
            continue

        if size <= 0:
            summary.error_count += 1
            if recorder:
                recorder.error('File appears corrupted because it is empty', path=file, code=ScanErrorCode.FILE_CORRUPTED)
            continue
        files.append(file)
    return files


def _upsert_work(
    session: Session,
    entry: Path,
    work_type: WorkType,
    files: list[Path],
    summary: ScanSummary,
    recorder: ScanRecorder | None,
    sidecar_payload: dict | None = None,
) -> None:
    work = session.scalar(
        select(Work)
        .options(selectinload(Work.files), selectinload(Work.tags))
        .where(Work.path == str(entry))
    )

    if sidecar_payload is None:
        sidecar_payload = _load_sidecar_payload(entry, summary, recorder)

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

    _sync_tags_from_sidecar(session, work, sidecar_payload, recorder, entry)

    for index, file in enumerate(files):
        try:
            size_bytes = file.stat().st_size
        except PermissionError:
            summary.error_count += 1
            if recorder:
                recorder.error('Permission denied while recording file', path=file, code=ScanErrorCode.PERMISSION_DENIED)
            continue
        except OSError as error:
            summary.error_count += 1
            if recorder:
                recorder.error(f'Failed to record file metadata: {error}', path=file, code=ScanErrorCode.FILE_STAT_FAILED)
            continue

        media_file = MediaFile(
            work_id=work.id,
            name=file.name,
            path=str(file),
            kind='image' if file.suffix.lower() in IMAGE_EXTENSIONS else 'video',
            size_bytes=size_bytes,
            order_index=index,
        )
        work.files.append(media_file)


def _sync_tags_from_sidecar(
    session: Session,
    work: Work,
    sidecar_payload: dict | None,
    recorder: ScanRecorder | None = None,
    entry: Path | None = None,
) -> None:
    if not sidecar_payload:
        return

    raw_tag_names = sidecar_payload.get('tags') or []
    if not isinstance(raw_tag_names, list):
        if recorder:
            recorder.warning('Ignored sidecar tags because the value is not a list', path=entry)
        return

    normalized_tag_names = [tag_name.strip() for tag_name in raw_tag_names if isinstance(tag_name, str) and tag_name.strip()]
    if not normalized_tag_names:
        return

    existing_names = {tag.name for tag in work.tags}
    for tag_name in normalized_tag_names:
        if tag_name in existing_names:
            continue
        work.tags.append(_get_or_create_tag(session, tag_name))
        existing_names.add(tag_name)


def _get_or_create_tag(session: Session, name: str) -> Tag:
    normalized = name.strip()
    tag = session.scalar(select(Tag).where(Tag.name == normalized))
    if tag is None:
        tag = Tag(name=normalized)
        session.add(tag)
        session.flush()
    return tag
