from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class WorkType(str, Enum):
    COMIC = "comic"
    VIDEO = "video"


work_tags = Table(
    "work_tags",
    Base.metadata,
    Column("work_id", ForeignKey("works.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class Work(Base):
    __tablename__ = "works"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    path: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    type: Mapped[WorkType] = mapped_column(SqlEnum(WorkType), index=True)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    cover_path: Mapped[str | None] = mapped_column(String(1024), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    files: Mapped[list[MediaFile]] = relationship(back_populates="work", cascade="all, delete-orphan")
    tags: Mapped[list[Tag]] = relationship(secondary=work_tags, back_populates="works")


class MediaRoot(Base):
    __tablename__ = "media_roots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(default=True)


class MediaFile(Base):
    __tablename__ = "media_files"
    __table_args__ = (UniqueConstraint("work_id", "path", name="uq_media_files_work_path"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("works.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(1024), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, default=None)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    work: Mapped[Work] = relationship(back_populates="files")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    color: Mapped[str | None] = mapped_column(String(16), default=None)
    group_name: Mapped[str | None] = mapped_column(String(64), default=None)

    works: Mapped[list[Work]] = relationship(secondary=work_tags, back_populates="tags")
