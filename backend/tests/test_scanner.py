import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import ScanTaskStatus, Tag, Work
from app.services.scanner import scan_library
from app.services.sidecar import SidecarParseError, export_work_sidecar, import_work_sidecar, load_sidecar_for_path


@pytest.fixture()
def session():
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with TestingSession() as db:
        yield db


def test_scan_library_creates_comic_and_video(tmp_path: Path, session):
    comic_dir = tmp_path / 'Comic A'
    comic_dir.mkdir()
    (comic_dir / '001.jpg').write_bytes(b'image')
    (tmp_path / 'movie.mp4').write_bytes(b'video')

    summary = scan_library(session, tmp_path)
    works = session.query(Work).all()

    assert summary.discovered == 2
    assert summary.created == 2
    assert summary.error_count == 0
    assert len(works) == 2


def test_scan_library_imports_sidecar_metadata_and_merges_tags(tmp_path: Path, session):
    comic_dir = tmp_path / 'Comic Sidecar'
    comic_dir.mkdir()
    (comic_dir / '001.jpg').write_bytes(b'image')
    (comic_dir / 'metadata.json').write_text(
        json.dumps({'title': 'Sidecar Title', 'description': 'Loaded from sidecar', 'tags': ['已整理', '收藏']}),
        encoding='utf-8',
    )

    scan_library(session, tmp_path)
    work = session.scalar(select(Work).where(Work.path == str(comic_dir)))
    assert work is not None

    existing_tag = session.scalar(select(Tag).where(Tag.name == '收藏'))
    assert existing_tag is not None
    work.tags = [existing_tag]
    session.commit()

    (comic_dir / 'metadata.json').write_text(
        json.dumps({'title': 'Sidecar Title', 'description': 'Loaded from sidecar', 'tags': ['收藏', '连载中']}),
        encoding='utf-8',
    )
    summary = scan_library(session, tmp_path)
    session.refresh(work)

    assert summary.updated == 1
    assert sorted(tag.name for tag in work.tags) == ['收藏', '连载中']


def test_load_sidecar_for_path_raises_parse_error_for_invalid_json(tmp_path: Path):
    comic_dir = tmp_path / 'Broken Sidecar'
    comic_dir.mkdir()
    (comic_dir / 'metadata.json').write_text('{invalid', encoding='utf-8')

    with pytest.raises(SidecarParseError) as exc_info:
        load_sidecar_for_path(comic_dir)

    assert 'invalid json' in str(exc_info.value)
    assert exc_info.value.sidecar_path == comic_dir / 'metadata.json'


def test_scan_library_reports_sidecar_parse_and_corrupted_file_errors(tmp_path: Path, session):
    comic_dir = tmp_path / 'Broken Comic'
    comic_dir.mkdir()
    (comic_dir / '001.jpg').write_bytes(b'')
    (comic_dir / 'metadata.json').write_text('{invalid', encoding='utf-8')

    summary = scan_library(session, tmp_path)

    assert summary.discovered == 0
    assert summary.skipped == 1
    assert summary.error_count == 2
    assert session.scalars(select(Work)).all() == []


def test_scan_library_returns_empty_summary_for_missing_root(tmp_path: Path, session):
    missing_root = tmp_path / 'missing'

    summary = scan_library(session, missing_root)

    assert summary.discovered == 0
    assert summary.error_count == 1


def test_export_and_import_sidecar_round_trip(tmp_path: Path, session):
    comic_dir = tmp_path / 'Comic Export'
    comic_dir.mkdir()
    (comic_dir / '001.jpg').write_bytes(b'image')

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
    payload['tags'] = ['导入标签']
    sidecar_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    import_work_sidecar(session, work.id)
    session.refresh(work)

    assert work.title == 'Imported Title'
    assert [tag.name for tag in work.tags] == ['导入标签']
