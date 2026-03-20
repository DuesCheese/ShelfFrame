from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app
from app.models import ScanTaskStatus


@pytest.fixture()
def client(tmp_path: Path):
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_session():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_scan_task_endpoints_record_errors_and_detail_logs(client: TestClient, tmp_path: Path):
    root = tmp_path / 'library'
    root.mkdir()
    comic_dir = root / 'Broken Comic'
    comic_dir.mkdir()
    (comic_dir / '001.jpg').write_bytes(b'')
    (comic_dir / 'metadata.json').write_text('{invalid', encoding='utf-8')

    response = client.post('/api/scan', json={'root': str(root)})
    assert response.status_code == 200
    payload = response.json()

    assert payload['discovered'] == 0
    assert payload['tasks'][0]['status'] == ScanTaskStatus.COMPLETED_WITH_ERRORS.value
    assert payload['tasks'][0]['error_message']

    list_response = client.get('/api/scan/tasks')
    assert list_response.status_code == 200
    tasks = list_response.json()
    assert len(tasks) == 1
    assert tasks[0]['logs']

    detail_response = client.get(f"/api/scan/tasks/{tasks[0]['id']}")
    assert detail_response.status_code == 200
    codes = {log['code'] for log in detail_response.json()['logs'] if log['code']}
    assert 'sidecar_parse_failed' in codes
    assert 'file_corrupted' in codes


def test_scan_task_detail_returns_404_when_missing(client: TestClient):
    response = client.get('/api/scan/tasks/999')

    assert response.status_code == 404
    assert response.json()['detail'] == 'Scan task not found'


def test_settings_media_root_management_validates_file_path(client: TestClient, tmp_path: Path):
    invalid_path = tmp_path / 'video.mp4'
    invalid_path.write_bytes(b'video')

    invalid_response = client.post('/api/settings/media-roots', json={'path': str(invalid_path)})
    assert invalid_response.status_code == 400
    assert invalid_response.json()['detail'] == 'Media root must be a directory path'

    valid_dir = tmp_path / 'library'
    valid_dir.mkdir()
    create_response = client.post('/api/settings/media-roots', json={'path': str(valid_dir)})
    assert create_response.status_code == 201
    duplicate_response = client.post('/api/settings/media-roots', json={'path': str(valid_dir)})
    assert duplicate_response.status_code == 201
    assert duplicate_response.json()['id'] == create_response.json()['id']

    missing_delete = client.delete('/api/settings/media-roots/999')
    assert missing_delete.status_code == 404
    assert missing_delete.json()['detail'] == 'Media root not found'


def test_work_detail_and_sidecar_import_errors_are_reported(client: TestClient, tmp_path: Path):
    root = tmp_path / 'library'
    root.mkdir()
    comic_dir = root / 'Comic A'
    comic_dir.mkdir()
    (comic_dir / '001.jpg').write_bytes(b'image')

    client.post('/api/scan', json={'root': str(root)})
    works_response = client.get('/api/works')
    work = works_response.json()[0]

    missing_work = client.get('/api/works/999')
    assert missing_work.status_code == 404
    assert missing_work.json()['detail'] == 'Work not found'

    import_response = client.post(f"/api/works/{work['id']}/import-sidecar")
    assert import_response.status_code == 404
    assert 'Sidecar not found' in import_response.json()['detail']


def test_tag_endpoints_cover_duplicate_and_missing_delete(client: TestClient):
    create_response = client.post('/api/tags', json={'name': '收藏', 'color': '#fff'})
    assert create_response.status_code == 201

    duplicate_response = client.post('/api/tags', json={'name': ' 收藏 '})
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()['detail'] == 'Tag already exists'

    list_response = client.get('/api/tags')
    assert list_response.status_code == 200
    assert [tag['name'] for tag in list_response.json()] == ['收藏']

    missing_delete = client.delete('/api/tags/999')
    assert missing_delete.status_code == 404
    assert missing_delete.json()['detail'] == 'Tag not found'
