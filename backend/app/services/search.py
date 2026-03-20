from __future__ import annotations

from sqlalchemy import Select, exists, func, or_, select

from app.models import Tag, Work, WorkType, work_tags


SearchableWorkSelect = Select[tuple[Work]]


def apply_work_filters(
    query: SearchableWorkSelect,
    *,
    work_type: WorkType | None = None,
    tag: str | None = None,
    search_term: str | None = None,
) -> SearchableWorkSelect:
    if work_type is not None:
        query = query.where(Work.type == work_type)

    normalized_tag = tag.strip() if tag else None
    if normalized_tag:
        query = query.where(
            exists(
                select(1)
                .select_from(work_tags.join(Tag, work_tags.c.tag_id == Tag.id))
                .where(work_tags.c.work_id == Work.id, Tag.name == normalized_tag)
            )
        )

    normalized_term = search_term.strip() if search_term else None
    if normalized_term:
        like_term = f'%{normalized_term.lower()}%'
        query = query.where(
            or_(
                func.lower(Work.title).like(like_term),
                func.lower(func.coalesce(Work.summary, '')).like(like_term),
                exists(
                    select(1)
                    .select_from(work_tags.join(Tag, work_tags.c.tag_id == Tag.id))
                    .where(
                        work_tags.c.work_id == Work.id,
                        func.lower(Tag.name).like(like_term),
                    )
                ),
            )
        )

    return query
