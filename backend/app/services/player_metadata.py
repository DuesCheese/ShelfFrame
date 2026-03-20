from __future__ import annotations

import json
import math
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlaybackEvent, PlaybackEventType, Work, WorkType
from app.schemas import HeatmapBucketRead, HoverThumbnailManifestRead, HoverThumbnailRead, VideoChapterRead, VideoPlayerMetadataRead
from app.services.media_access import build_media_file_url
from app.services.sidecar import resolve_sidecar_path


def load_video_player_metadata(session: Session, work: Work) -> VideoPlayerMetadataRead:
    if work.type != WorkType.VIDEO:
        return VideoPlayerMetadataRead()

    payload = _load_sidecar_payload(work)
    video_payload = payload.get('video') if isinstance(payload.get('video'), dict) else {}
    chapters = _parse_chapters(video_payload.get('chapters'))
    thumbnails = _parse_hover_thumbnails(video_payload.get('hover_thumbnails'))
    source_url = build_media_file_url(work.files[0].id) if work.files else None
    heatmap = build_heatmap(session, work.id, chapters, _infer_duration(work, chapters, payload))
    return VideoPlayerMetadataRead(
        source_url=source_url,
        chapters=chapters,
        hover_thumbnails=thumbnails,
        heatmap=heatmap,
    )


def record_playback_event(session: Session, work: Work, event_type: PlaybackEventType, to_seconds: float, from_seconds: float | None = None, duration_seconds: float | None = None) -> None:
    session.add(
        PlaybackEvent(
            work_id=work.id,
            event_type=event_type,
            from_seconds=from_seconds,
            to_seconds=to_seconds,
            duration_seconds=duration_seconds,
        )
    )
    session.commit()


def build_heatmap(
    session: Session,
    work_id: int,
    chapters: list[VideoChapterRead],
    duration_hint: float | None,
) -> list[HeatmapBucketRead]:
    events = session.scalars(select(PlaybackEvent).where(PlaybackEvent.work_id == work_id).order_by(PlaybackEvent.created_at.asc())).all()
    if not events and not duration_hint:
        return []

    duration = duration_hint or _derive_duration_from_events(events) or 0.0
    if duration <= 0:
        return []

    bucket_count = max(6, min(24, math.ceil(duration / 30) or 6))
    bucket_width = duration / bucket_count
    counts = [0] * bucket_count

    for event in events:
        lower = max(0.0, min(event.from_seconds if event.from_seconds is not None else event.to_seconds, event.to_seconds))
        upper = max(lower, max(event.to_seconds, event.from_seconds or event.to_seconds))
        if event.event_type == PlaybackEventType.SEEK and lower == upper:
            upper = min(duration, lower + max(bucket_width * 0.25, 1.0))
        if upper == lower:
            upper = min(duration, lower + max(bucket_width * 0.5, 1.0))
        start_index = min(bucket_count - 1, int(lower / bucket_width))
        end_index = min(bucket_count - 1, int((max(upper - 0.001, 0.0)) / bucket_width))
        for index in range(start_index, end_index + 1):
            counts[index] += 1

    max_count = max(counts) if any(counts) else 1
    return [
        HeatmapBucketRead(
            start_seconds=round(index * bucket_width, 3),
            end_seconds=round(duration if index == bucket_count - 1 else (index + 1) * bucket_width, 3),
            intensity=round(count / max_count, 4),
            event_count=count,
        )
        for index, count in enumerate(counts)
    ]


def _load_sidecar_payload(work: Work) -> dict:
    sidecar_path = resolve_sidecar_path(work)
    if not sidecar_path.exists():
        return {}
    try:
        return json.loads(sidecar_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {}


def _parse_chapters(raw_value: object) -> list[VideoChapterRead]:
    if not isinstance(raw_value, list):
        return []

    chapters: list[VideoChapterRead] = []
    for index, item in enumerate(raw_value):
        if not isinstance(item, dict):
            continue
        label = str(item.get('label') or f'章节 {index + 1}').strip()
        start_seconds = _coerce_float(item.get('start_seconds'))
        end_seconds = _coerce_float(item.get('end_seconds'))
        if start_seconds is None or end_seconds is None or end_seconds <= start_seconds:
            continue
        chapters.append(
            VideoChapterRead(
                label=label,
                start_seconds=round(start_seconds, 3),
                end_seconds=round(end_seconds, 3),
            )
        )
    return sorted(chapters, key=lambda chapter: chapter.start_seconds)


def _parse_hover_thumbnails(raw_value: object) -> HoverThumbnailManifestRead:
    if not isinstance(raw_value, dict):
        return HoverThumbnailManifestRead()

    status = str(raw_value.get('status') or 'pending')
    items_raw = raw_value.get('items') if isinstance(raw_value.get('items'), list) else []
    items: list[HoverThumbnailRead] = []
    for item in items_raw:
        if not isinstance(item, dict):
            continue
        time_seconds = _coerce_float(item.get('time_seconds'))
        image_url = item.get('image_url')
        if time_seconds is None or not isinstance(image_url, str) or not image_url:
            continue
        items.append(
            HoverThumbnailRead(
                time_seconds=round(time_seconds, 3),
                image_url=image_url,
                width=_coerce_int(item.get('width')),
                height=_coerce_int(item.get('height')),
            )
        )
    return HoverThumbnailManifestRead(status=status, items=sorted(items, key=lambda item: item.time_seconds))


def _derive_duration_from_events(events: list[PlaybackEvent]) -> float | None:
    values = [event.duration_seconds for event in events if event.duration_seconds and event.duration_seconds > 0]
    if values:
        return max(values)
    positions = [event.to_seconds for event in events if event.to_seconds >= 0]
    return max(positions) if positions else None


def _infer_duration(work: Work, chapters: list[VideoChapterRead], payload: dict) -> float | None:
    video_payload = payload.get('video') if isinstance(payload.get('video'), dict) else {}
    duration = _coerce_float(video_payload.get('duration_seconds'))
    if duration and duration > 0:
        return duration
    if chapters:
        return max(chapter.end_seconds for chapter in chapters)
    if work.files:
        try:
            return max(Path(media_file.path).stat().st_size for media_file in work.files) / 1_000_000
        except OSError:
            return None
    return None


def _coerce_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _coerce_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
