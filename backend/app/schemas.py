from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.models import PlaybackEventType, WorkType


class FileRead(BaseModel):
    id: int
    name: str
    path: str
    kind: str
    size_bytes: int | None
    order_index: int
    content_url: str | None = None


class ThumbnailRead(BaseModel):
    id: int
    type: ThumbnailType
    source_path: str | None = None
    image_path: str
    ts_sec: int | None = None
    sort_no: int
    thumbnail_url: str


class TagCreate(BaseModel):
    name: str
    color: str | None = None
    group_name: str | None = None


class TagRead(BaseModel):
    id: int
    name: str
    color: str | None = None
    group_name: str | None = None


class MediaRootCreate(BaseModel):
    path: Path


class MediaRootRead(BaseModel):
    id: int
    path: str
    enabled: bool


class VideoChapterRead(BaseModel):
    label: str
    start_seconds: float
    end_seconds: float


class HoverThumbnailRead(BaseModel):
    time_seconds: float
    image_url: str
    width: int | None = None
    height: int | None = None


class HoverThumbnailManifestRead(BaseModel):
    status: str = 'pending'
    items: list[HoverThumbnailRead] = Field(default_factory=list)


class HeatmapBucketRead(BaseModel):
    start_seconds: float
    end_seconds: float
    intensity: float
    event_count: int


class VideoPlayerMetadataRead(BaseModel):
    source_url: str | None = None
    chapters: list[VideoChapterRead] = Field(default_factory=list)
    hover_thumbnails: HoverThumbnailManifestRead = Field(default_factory=HoverThumbnailManifestRead)
    heatmap: list[HeatmapBucketRead] = Field(default_factory=list)


class WorkRead(BaseModel):
    id: int
    title: str
    path: str
    type: WorkType
    summary: str | None = None
    cover_path: str | None = None
    cover_url: str | None = None
    created_at: datetime
    updated_at: datetime
    tags: list[TagRead] = Field(default_factory=list)
    files: list[FileRead] = Field(default_factory=list)
    player_metadata: VideoPlayerMetadataRead | None = None


class ScanRequest(BaseModel):
    root: Path | None = None


class ScanResult(BaseModel):
    discovered: int
    created: int
    updated: int
    skipped: int
    roots: list[str] = Field(default_factory=list)


class SettingRead(BaseModel):
    database_url: str
    media_roots: list[MediaRootRead] = Field(default_factory=list)


class SidecarActionResult(BaseModel):
    work_id: int
    sidecar_path: str
    action: str


class PlaybackEventCreate(BaseModel):
    event_type: PlaybackEventType
    from_seconds: float | None = None
    to_seconds: float = Field(ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)


class PlaybackEventAck(BaseModel):
    work_id: int
    accepted: bool


class MediaFileUrlRead(BaseModel):
    file_id: int
    url: str
