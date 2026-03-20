from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.models import ActivityEventType, ThumbnailType, WorkType


class FileRead(BaseModel):
    id: int
    name: str
    path: str
    kind: str
    size_bytes: int | None
    order_index: int


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
