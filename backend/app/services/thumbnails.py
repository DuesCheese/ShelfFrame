from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import MediaFile, Thumbnail, ThumbnailType, Work, WorkType

COMIC_THUMBNAIL_LIMIT = 8
VIDEO_THUMBNAIL_TIMESTAMPS = (0, 10, 30)


def get_thumbnail_root() -> Path:
    root = settings.media_root.expanduser().resolve() / ".cache" / "thumbnails"
    root.mkdir(parents=True, exist_ok=True)
    return root


def generate_work_thumbnails(session: Session, work_id: int, *, force: bool = False) -> list[Thumbnail]:
    work = session.scalar(
        select(Work)
        .options(selectinload(Work.files), selectinload(Work.thumbnails))
        .where(Work.id == work_id)
    )
    if work is None:
        raise ValueError(f"Work {work_id} not found")

    if force:
        for thumbnail in list(work.thumbnails):
            _safe_unlink(Path(thumbnail.image_path))
        work.thumbnails.clear()
        session.flush()

    existing = sorted(work.thumbnails, key=lambda item: item.sort_no)
    if existing and not force:
        return existing

    thumbnail_dir = get_thumbnail_root() / str(work.id)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Thumbnail] = []
    if work.type == WorkType.COMIC:
        image_files = [media_file for media_file in sorted(work.files, key=lambda item: item.order_index) if media_file.kind == "image"]
        generated = _generate_comic_thumbnails(work, image_files[:COMIC_THUMBNAIL_LIMIT], thumbnail_dir)
    else:
        video_file = next((media_file for media_file in sorted(work.files, key=lambda item: item.order_index) if media_file.kind == "video"), None)
        if video_file is not None:
            generated = _generate_video_thumbnails(work, video_file, thumbnail_dir)

    for thumbnail in generated:
        session.add(thumbnail)
    session.flush()

    if generated and (not work.cover_path or force):
        work.cover_path = generated[0].image_path

    session.commit()
    return sorted(work.thumbnails, key=lambda item: item.sort_no)


def get_current_cover_thumbnail(work: Work) -> Thumbnail | None:
    if not work.cover_path:
        return None
    return next((item for item in work.thumbnails if item.image_path == work.cover_path), None)


def set_work_cover(session: Session, work_id: int, thumbnail_id: int) -> Work:
    work = session.scalar(select(Work).options(selectinload(Work.thumbnails)).where(Work.id == work_id))
    if work is None:
        raise ValueError(f"Work {work_id} not found")

    thumbnail = next((item for item in work.thumbnails if item.id == thumbnail_id), None)
    if thumbnail is None:
        raise ValueError(f"Thumbnail {thumbnail_id} not found for work {work_id}")

    work.cover_path = thumbnail.image_path
    session.commit()
    session.refresh(work)
    return work


def _generate_comic_thumbnails(work: Work, image_files: Iterable[MediaFile], thumbnail_dir: Path) -> list[Thumbnail]:
    generated: list[Thumbnail] = []
    for sort_no, media_file in enumerate(image_files):
        source = Path(media_file.path)
        extension = source.suffix.lower() or ".jpg"
        target = thumbnail_dir / f"comic-{sort_no:03d}{extension}"
        if not target.exists():
            shutil.copy2(source, target)
        generated.append(
            Thumbnail(
                work_id=work.id,
                type=ThumbnailType.COVER,
                source_path=media_file.path,
                image_path=str(target),
                sort_no=sort_no,
            )
        )
    return generated


def _generate_video_thumbnails(work: Work, video_file: MediaFile, thumbnail_dir: Path) -> list[Thumbnail]:
    generated: list[Thumbnail] = []
    ffmpeg_path = shutil.which("ffmpeg")
    for sort_no, ts_sec in enumerate(VIDEO_THUMBNAIL_TIMESTAMPS):
        target = thumbnail_dir / f"video-{sort_no:03d}.jpg"
        if ffmpeg_path:
            _extract_video_frame(ffmpeg_path, Path(video_file.path), ts_sec, target)
        if not target.exists():
            target = thumbnail_dir / f"video-{sort_no:03d}.svg"
            _write_video_placeholder(target, work.title, ts_sec)
        generated.append(
            Thumbnail(
                work_id=work.id,
                type=ThumbnailType.KEYFRAME,
                source_path=video_file.path,
                image_path=str(target),
                ts_sec=ts_sec,
                sort_no=sort_no,
            )
        )
    return generated


def _extract_video_frame(ffmpeg_path: str, video_path: Path, ts_sec: int, target: Path) -> None:
    if target.exists():
        return
    try:
        subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-ss",
                str(ts_sec),
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(target),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        _safe_unlink(target)


def _write_video_placeholder(path: Path, title: str, ts_sec: int) -> None:
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='640' height='360' viewBox='0 0 640 360'>
  <defs>
    <linearGradient id='bg' x1='0' x2='1' y1='0' y2='1'>
      <stop offset='0%' stop-color='#1d4ed8'/>
      <stop offset='100%' stop-color='#7c3aed'/>
    </linearGradient>
  </defs>
  <rect width='640' height='360' rx='24' fill='url(#bg)'/>
  <text x='50%' y='45%' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='32' fill='white'>视频缩略图</text>
  <text x='50%' y='58%' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='20' fill='#dbeafe'>{title}</text>
  <text x='50%' y='70%' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='24' fill='#e0e7ff'>时间点 {ts_sec}s</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def _safe_unlink(path: Path) -> None:
    if path.exists():
        path.unlink()
