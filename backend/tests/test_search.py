from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import Tag, Work, WorkType
from app.db import Base
from app.services.search import apply_work_filters


def create_session():
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSession()


def create_work(session, *, title: str, summary: str | None = None, work_type: WorkType = WorkType.COMIC, tags: list[str] | None = None):
    work = Work(title=title, summary=summary, path=f'/library/{title}', type=work_type)
    if tags:
        work.tags = [_get_or_create_tag(session, tag_name) for tag_name in tags]
    session.add(work)
    session.commit()
    return work



def _get_or_create_tag(session, name: str) -> Tag:
    tag = session.scalar(select(Tag).where(Tag.name == name))
    if tag is None:
        tag = Tag(name=name)
        session.add(tag)
        session.flush()
    return tag



def run_search(session, *, work_type: WorkType | None = None, tag: str | None = None, search_term: str | None = None):
    query = select(Work).order_by(Work.id.asc())
    query = apply_work_filters(query, work_type=work_type, tag=tag, search_term=search_term)
    return session.scalars(query).all()



def test_search_matches_title():
    with create_session() as session:
        create_work(session, title='银河列车 999', summary='经典科幻')
        create_work(session, title='海边写真', summary='旅行影像')

        works = run_search(session, search_term='银河')

    assert [work.title for work in works] == ['银河列车 999']



def test_search_matches_summary_with_fuzzy_like():
    with create_session() as session:
        create_work(session, title='晨间漫画', summary='关于校园推理事件的短篇合集')
        create_work(session, title='夜间电影', summary='都市爱情')

        works = run_search(session, search_term='推理')

    assert [work.title for work in works] == ['晨间漫画']



def test_search_matches_tag_name():
    with create_session() as session:
        create_work(session, title='作品 A', tags=['悬疑'])
        create_work(session, title='作品 B', tags=['轻松'])

        works = run_search(session, search_term='悬')

    assert [work.title for work in works] == ['作品 A']



def test_search_combines_with_type_and_tag_filters():
    with create_session() as session:
        create_work(session, title='漫画侦探档案', summary='案件合集', work_type=WorkType.COMIC, tags=['已整理'])
        create_work(session, title='视频侦探档案', summary='案件回顾', work_type=WorkType.VIDEO, tags=['已整理'])
        create_work(session, title='漫画恋爱日记', summary='校园生活', work_type=WorkType.COMIC, tags=['收藏'])

        works = run_search(session, work_type=WorkType.COMIC, tag='已整理', search_term='侦探')

    assert [work.title for work in works] == ['漫画侦探档案']



def test_search_ignores_blank_search_term():
    with create_session() as session:
        create_work(session, title='作品 A')
        create_work(session, title='作品 B')

        works = run_search(session, search_term='   ')

    assert [work.title for work in works] == ['作品 A', '作品 B']
