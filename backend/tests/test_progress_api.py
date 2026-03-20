from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app
from app.models import MediaFile, ReadingProgress, Work, WorkType


def create_client(tmp_path: Path) -> tuple[TestClient, sessionmaker]:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_session():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    return client, TestingSession


def seed_work(SessionLocal: sessionmaker, tmp_path: Path) -> tuple[Work, int]:
    image_dir = tmp_path / 'Comic Progress'
    image_dir.mkdir()
    image_path = image_dir / '001.jpg'
    image_path.write_bytes(b'image-content')

    with SessionLocal() as session:
        work = Work(title='Comic Progress', path=str(image_dir), type=WorkType.COMIC, cover_path=str(image_path))
        session.add(work)
        session.flush()
        session.add(MediaFile(work_id=work.id, name='001.jpg', path=str(image_path), kind='image', order_index=0, size_bytes=13))
        session.commit()
        session.refresh(work)
        file_id = session.scalar(select(MediaFile.id).where(MediaFile.work_id == work.id))
        return work, file_id


def test_progress_endpoint_returns_none_for_first_visit(tmp_path: Path):
    client, SessionLocal = create_client(tmp_path)
    work, _ = seed_work(SessionLocal, tmp_path)

    response = client.get(f'/api/progress/{work.id}')

    assert response.status_code == 200
    assert response.json() is None
    app.dependency_overrides.clear()


def test_progress_endpoint_persists_and_restores_progress(tmp_path: Path):
    client, SessionLocal = create_client(tmp_path)
    work, _ = seed_work(SessionLocal, tmp_path)

    save_response = client.put(
        f'/api/progress/{work.id}',
        json={'chapter_key': None, 'file_index': 0, 'page': 1, 'position': 0.35},
    )
    load_response = client.get(f'/api/progress/{work.id}')

    assert save_response.status_code == 200
    assert load_response.status_code == 200
    assert load_response.json()['position'] == 0.35

    with SessionLocal() as session:
        stored = session.scalar(select(ReadingProgress).where(ReadingProgress.work_id == work.id))
        assert stored is not None
        assert stored.page == 1
    app.dependency_overrides.clear()


def test_work_payload_exposes_progress_and_image_content_url(tmp_path: Path):
    client, SessionLocal = create_client(tmp_path)
    work, _ = seed_work(SessionLocal, tmp_path)
    client.put(f'/api/progress/{work.id}', json={'file_index': 0, 'page': 1, 'position': 0.5})

    response = client.get(f'/api/works/{work.id}')

    assert response.status_code == 200
    payload = response.json()
    assert payload['progress']['work_id'] == work.id
    assert payload['files'][0]['content_url'].endswith('/content')
    app.dependency_overrides.clear()


def test_work_file_content_route_streams_image(tmp_path: Path):
    client, SessionLocal = create_client(tmp_path)
    work, file_id = seed_work(SessionLocal, tmp_path)

    response = client.get(f'/api/works/{work.id}/files/{file_id}/content')

    assert response.status_code == 200
    assert response.content == b'image-content'
    app.dependency_overrides.clear()
