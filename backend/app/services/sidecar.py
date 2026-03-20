from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Tag, Work, WorkType


SIDE_CAR_FILENAME = 'metadata.json'
VIDEO_SIDE_CAR_SUFFIX = '.metadata.json'
DEFAULT_VIDEO_METADATA = {
    'duration_seconds': None,
    'chapters': [],
    'hover_thumbnails': {
        'status': 'pending',
        'items': [],
    },
}


def resolve_sidecar_path(work: Work) -> Path:
    work_path = Path(work.path)
    if work_path.is_dir() or work.type.value == 'comic':
        return work_path / SIDE_CAR_FILENAME
    return work_path.with_suffix(VIDEO_SIDE_CAR_SUFFIX)


def load_sidecar_for_path(entry: Path) -> dict | None:
    sidecar_path = entry / SIDE_CAR_FILENAME if entry.is_dir() else entry.with_suffix(VIDEO_SIDE_CAR_SUFFIX)
    if not sidecar_path.exists():
        return None
    return json.loads(sidecar_path.read_text(encoding='utf-8'))


def export_work_sidecar(session: Session, work_id: int) -> Path:
    work = session.scalar(select(Work).options(selectinload(Work.files), selectinload(Work.tags)).where(Work.id == work_id))
    if work is None:
        raise ValueError(f'Work {work_id} not found')

    sidecar_path = resolve_sidecar_path(work)
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    current_payload = _load_existing_payload(sidecar_path)
    payload = {
        'schema_version': 2,
        'work_id': work.id,
        'type': work.type.value,
        'title': work.title,
        'description': work.summary,
        'cover_path': work.cover_path,
        'tags': [tag.name for tag in work.tags],
        'files': [
            {
                'name': media_file.name,
                'path': media_file.path,
                'kind': media_file.kind,
                'order_index': media_file.order_index,
            }
            for media_file in sorted(work.files, key=lambda item: item.order_index)
        ],
    }
    if work.type == WorkType.VIDEO:
        payload['video'] = _merge_video_payload(current_payload.get('video'))
    sidecar_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return sidecar_path


def import_work_sidecar(session: Session, work_id: int) -> Path:
    work = session.scalar(select(Work).options(selectinload(Work.tags)).where(Work.id == work_id))
    if work is None:
        raise ValueError(f'Work {work_id} not found')

    sidecar_path = resolve_sidecar_path(work)
    if not sidecar_path.exists():
        raise FileNotFoundError(sidecar_path)

    payload = json.loads(sidecar_path.read_text(encoding='utf-8'))
    work.title = payload.get('title') or work.title
    work.summary = payload.get('description')
    work.cover_path = payload.get('cover_path') or work.cover_path

    tag_names = payload.get('tags') or []
    if tag_names:
        work.tags = [_get_or_create_tag(session, tag_name) for tag_name in tag_names]

    session.add(work)
    session.commit()
    session.refresh(work)
    return sidecar_path


def _get_or_create_tag(session: Session, name: str) -> Tag:
    normalized = name.strip()
    tag = session.scalar(select(Tag).where(Tag.name == normalized))
    if tag is None:
        tag = Tag(name=normalized)
        session.add(tag)
        session.flush()
    return tag


def _load_existing_payload(sidecar_path: Path) -> dict:
    if not sidecar_path.exists():
        return {}
    try:
        return json.loads(sidecar_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {}


def _merge_video_payload(raw_value: object) -> dict:
    payload = DEFAULT_VIDEO_METADATA | (raw_value if isinstance(raw_value, dict) else {})
    hover_thumbnails = DEFAULT_VIDEO_METADATA['hover_thumbnails'] | (
        payload.get('hover_thumbnails') if isinstance(payload.get('hover_thumbnails'), dict) else {}
    )
    payload['hover_thumbnails'] = hover_thumbnails
    payload['chapters'] = payload.get('chapters') if isinstance(payload.get('chapters'), list) else []
    return payload
