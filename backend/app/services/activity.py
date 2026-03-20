from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import ActivityEvent, ActivityEventType, Work


def record_activity_event(
    session: Session,
    *,
    work_id: int,
    event_type: ActivityEventType,
    payload: dict | None = None,
) -> ActivityEvent:
    work = session.get(Work, work_id)
    if work is None:
        raise ValueError(f"Work {work_id} not found")

    event = ActivityEvent(
        work_id=work_id,
        event_type=event_type,
        at_time=datetime.now(timezone.utc),
        payload_json=json.dumps(payload, ensure_ascii=False) if payload else None,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def list_recent_work_activity(session: Session, limit: int = 8) -> list[tuple[Work, ActivityEvent]]:
    ranked_events = (
        select(
            ActivityEvent.id.label("event_id"),
            ActivityEvent.work_id.label("work_id"),
            func.row_number()
            .over(partition_by=ActivityEvent.work_id, order_by=(ActivityEvent.at_time.desc(), ActivityEvent.id.desc()))
            .label("rank_no"),
        )
        .subquery()
    )
    query = (
        select(Work, ActivityEvent)
        .join(ranked_events, ranked_events.c.work_id == Work.id)
        .join(ActivityEvent, ActivityEvent.id == ranked_events.c.event_id)
        .options(selectinload(Work.files), selectinload(Work.tags), selectinload(Work.thumbnails))
        .where(ranked_events.c.rank_no == 1)
        .order_by(ActivityEvent.at_time.desc(), ActivityEvent.id.desc())
        .limit(limit)
    )
    return list(session.execute(query).all())
