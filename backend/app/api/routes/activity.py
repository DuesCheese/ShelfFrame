from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import ActivityEventType
from app.schemas import ActivityEventCreate, ActivityEventRead, RecentActivityRead, WorkRead
from app.services.activity import list_recent_work_activity, record_activity_event
from app.api.routes.works import _serialize_work

router = APIRouter(prefix='/activity-events', tags=['activity-events'])


@router.post('', response_model=ActivityEventRead)
def create_activity_event(payload: ActivityEventCreate, session: Session = Depends(get_session)) -> ActivityEventRead:
    try:
        event = record_activity_event(
            session,
            work_id=payload.work_id,
            event_type=payload.event_type,
            payload=payload.payload,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return ActivityEventRead.model_validate(event, from_attributes=True)


@router.get('/recent', response_model=list[RecentActivityRead])
def get_recent_activity(
    limit: int = Query(default=8, ge=1, le=50),
    session: Session = Depends(get_session),
) -> list[RecentActivityRead]:
    rows = list_recent_work_activity(session, limit=limit)
    return [
        RecentActivityRead(
            work=_serialize_work(work),
            last_event=ActivityEventRead.model_validate(event, from_attributes=True),
        )
        for work, event in rows
    ]
