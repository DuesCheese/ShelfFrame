from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.models import ScanLogLevel, ScanTaskStatus, WorkType


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


class ReadingProgressRead(BaseModel):
    work_id: int
    chapter_key: str | None = None
    file_index: int = 0
    page: int = 1
    position: float = 0.0
    updated_at: datetime


class ReadingProgressUpsert(BaseModel):
    chapter_key: str | None = None
    file_index: int = 0
    page: int = 1
    position: float = 0.0


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
    thumbnails: list[ThumbnailRead] = Field(default_factory=list)
    current_cover: ThumbnailRead | None = None


class ScanRequest(BaseModel):
    root: Path | None = None


class ScanLogRead(BaseModel):
    id: int
    level: ScanLogLevel
    code: str | None = None
    path: str | None = None
    message: str
    created_at: datetime


class ScanTaskRead(BaseModel):
    id: int
    root_path: str
    status: ScanTaskStatus
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None
    discovered: int
    created: int
    updated: int
    skipped: int
    logs: list[ScanLogRead] = Field(default_factory=list)


class ScanRunResult(BaseModel):
    discovered: int
    created: int
    updated: int
    skipped: int
    roots: list[str] = Field(default_factory=list)
    tasks: list[ScanTaskRead] = Field(default_factory=list)


class SettingRead(BaseModel):
    database_url: str
    media_roots: list[MediaRootRead] = Field(default_factory=list)


class SidecarActionResult(BaseModel):
    work_id: int
    sidecar_path: str
    action: str


class ThumbnailGenerationResult(BaseModel):
    work_id: int
    generated: int
    action: str


class CoverSelectRequest(BaseModel):
    thumbnail_id: int


class ActivityEventCreate(BaseModel):
    work_id: int
    event_type: ActivityEventType
    payload: dict[str, Any] | None = None


class ActivityEventRead(BaseModel):
    id: int
    work_id: int
    event_type: ActivityEventType
    at_time: datetime
    payload_json: str | None = None


class RecentActivityRead(BaseModel):
    work: WorkRead
    last_event: ActivityEventRead
