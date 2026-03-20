from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Work
from app.services.scanner import scan_library


def test_scan_library_creates_comic_and_video(tmp_path: Path):
    comic_dir = tmp_path / "Comic A"
    comic_dir.mkdir()
    (comic_dir / "001.jpg").write_bytes(b"image")
    (tmp_path / "movie.mp4").write_bytes(b"video")

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with TestingSession() as session:
        summary = scan_library(session, tmp_path)
        works = session.query(Work).all()

    assert summary.discovered == 2
    assert len(works) == 2
