from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from app.models import WorkType


class FileRead(BaseModel):
    id: int
    name: str
    path: str
    kind: str
    size_bytes: int | None
    order_index: int


class TagRead(BaseModel):
    id: int
    name: str
    color: str | None = None
    group_name: str | None = None


class WorkRead(BaseModel):
    id: int
    title: str
    path: str
    type: WorkType
    summary: str | None = None
    cover_path: str | None = None
    created_at: datetime
    updated_at: datetime
    tags: list[TagRead] = Field(default_factory=list)
    files: list[FileRead] = Field(default_factory=list)


class ScanRequest(BaseModel):
    root: Path | None = None


class ScanResult(BaseModel):
    discovered: int
    created: int
    updated: int
    skipped: int


class SettingRead(BaseModel):
    database_url: str
    media_root: Path
