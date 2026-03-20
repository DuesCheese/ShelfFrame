import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db import Base
from app.models import MediaRoot, PlaybackEvent, PlaybackEventType, Tag, Work
from app.services.media_access import build_media_file_url, resolve_media_file_path
from app.services.media_roots import add_media_root, bootstrap_media_root
from app.services.player_metadata import load_video_player_metadata, record_playback_event
from app.services.scanner import scan_library
from app.services.sidecar import export_work_sidecar, import_work_sidecar


def create_session():
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSession()


def test_scan_library_creates_comic_and_video(tmp_path: Path):
    comic_dir = tmp_path / 'Comic A'
    comic_dir.mkdir()
    (comic_dir / '001.jpg').write_bytes(b'image')
    (tmp_path / 'movie.mp4').write_bytes(b'video')

    with create_session() as session:
        summary = scan_library(session, tmp_path)
        works = session.query(Work).all()

    assert summary.discovered == 2
    assert len(works) == 2


def test_scan_library_imports_sidecar_metadata(tmp_path: Path):
    comic_dir = tmp_path / 'Comic Sidecar'
    comic_dir.mkdir()
    (comic_dir / '001.jpg').write_bytes(b'image')
    (comic_dir / 'metadata.json').write_text(
        json.dumps({'title': 'Sidecar Title', 'description': 'Loaded from sidecar', 'tags': ['已整理', '收藏']}),
        encoding='utf-8',
    )

    with create_session() as session:
        scan_library(session, tmp_path)
        work = session.scalar(select(Work).where(Work.path == str(comic_dir)))
        tags = session.scalars(select(Tag).order_by(Tag.name.asc())).all()

    assert work is not None
    assert work.title == 'Sidecar Title'
    assert work.summary == 'Loaded from sidecar'
    assert sorted(tag.name for tag in tags) == ['已整理', '收藏']


def test_export_and_import_sidecar_round_trip(tmp_path: Path):
    comic_dir = tmp_path / 'Comic Export'
    comic_dir.mkdir()
    (comic_dir / '001.jpg').write_bytes(b'image')

    with create_session() as session:
        scan_library(session, tmp_path)
        work = session.scalar(select(Work).where(Work.path == str(comic_dir)))
        assert work is not None
        work.title = 'Edited Title'
        work.summary = 'Edited Summary'
        session.commit()

        sidecar_path = export_work_sidecar(session, work.id)
        payload = json.loads(sidecar_path.read_text(encoding='utf-8'))
        assert payload['title'] == 'Edited Title'

        payload['title'] = 'Imported Title'
        sidecar_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        import_work_sidecar(session, work.id)
        session.refresh(work)

        assert work.title == 'Imported Title'


def test_video_player_metadata_reads_sidecar_and_aggregates_heatmap(tmp_path: Path):
    video_path = tmp_path / 'movie.mp4'
    video_path.write_bytes(b'video-content')
    sidecar_path = tmp_path / 'movie.metadata.json'
    sidecar_path.write_text(
        json.dumps(
            {
                'title': 'Movie',
                'video': {
                    'duration_seconds': 180,
                    'chapters': [
                        {'label': '片头', 'start_seconds': 0, 'end_seconds': 30},
                        {'label': '正片', 'start_seconds': 30, 'end_seconds': 180},
                    ],
                    'hover_thumbnails': {
                        'status': 'ready',
                        'items': [
                            {'time_seconds': 15, 'image_url': '/thumbs/movie-15.jpg', 'width': 160, 'height': 90},
                        ],
                    },
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )

    with create_session() as session:
        add_media_root(session, tmp_path)
        scan_library(session, tmp_path)
        work = session.scalar(select(Work).where(Work.path == str(video_path)))
        assert work is not None

        record_playback_event(session, work, event_type=PlaybackEventType.PLAY, to_seconds=12, duration_seconds=180)
        record_playback_event(session, work, event_type=PlaybackEventType.SEEK, from_seconds=12, to_seconds=75, duration_seconds=180)
        metadata = load_video_player_metadata(session, work)

    assert metadata.source_url == build_media_file_url(work.files[0].id)
    assert [chapter.label for chapter in metadata.chapters] == ['片头', '正片']
    assert metadata.hover_thumbnails.status == 'ready'
    assert metadata.hover_thumbnails.items[0].image_url == '/thumbs/movie-15.jpg'
    assert metadata.heatmap
    assert max(bucket.intensity for bucket in metadata.heatmap) == 1


def test_media_access_rejects_paths_outside_enabled_root(tmp_path: Path):
    disallowed_root = tmp_path / 'disallowed'
    disallowed_root.mkdir()
    video_path = disallowed_root / 'outside.mp4'
    video_path.write_bytes(b'video')

    with create_session() as session:
        scan_library(session, disallowed_root)
        work = session.scalar(select(Work).where(Work.path == str(video_path)))
        assert work is not None

        with pytest.raises(HTTPException) as error:
            resolve_media_file_path(session, work.files[0].id)

    assert error.value.status_code == 403


def test_bootstrap_and_add_media_root(tmp_path: Path):
    with create_session() as session:
        bootstrap_media_root(session)
        default_root = session.scalar(select(MediaRoot))
        assert default_root is not None
        assert default_root.path == str(settings.media_root.resolve())

        another_root = add_media_root(session, tmp_path / 'library')
        roots = session.scalars(select(MediaRoot).order_by(MediaRoot.id.asc())).all()

    assert another_root.path == str((tmp_path / 'library').resolve())
    assert len(roots) == 2


def test_record_playback_event_persists_rows(tmp_path: Path):
    video_path = tmp_path / 'single.mp4'
    video_path.write_bytes(b'video')

    with create_session() as session:
        add_media_root(session, tmp_path)
        scan_library(session, tmp_path)
        work = session.scalar(select(Work).where(Work.path == str(video_path)))
        assert work is not None

        record_playback_event(session, work, event_type=PlaybackEventType.SEEK, from_seconds=3, to_seconds=42, duration_seconds=60)
        events = session.scalars(select(PlaybackEvent).where(PlaybackEvent.work_id == work.id)).all()

    assert len(events) == 1
    assert events[0].to_seconds == 42
