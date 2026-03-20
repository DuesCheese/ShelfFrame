from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Tag
from app.schemas import TagCreate, TagRead

router = APIRouter(prefix='/tags', tags=['tags'])


@router.get('', response_model=list[TagRead])
def list_tags(session: Session = Depends(get_session)) -> list[TagRead]:
    tags = session.scalars(select(Tag).order_by(Tag.name.asc())).all()
    return [TagRead.model_validate(tag, from_attributes=True) for tag in tags]


@router.post('', response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagCreate, session: Session = Depends(get_session)) -> TagRead:
    normalized = payload.name.strip()
    tag = session.scalar(select(Tag).where(Tag.name == normalized))
    if tag is not None:
        raise HTTPException(status_code=409, detail='Tag already exists')

    tag = Tag(name=normalized, color=payload.color, group_name=payload.group_name)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return TagRead.model_validate(tag, from_attributes=True)


@router.delete('/{tag_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: int, session: Session = Depends(get_session)) -> Response:
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail='Tag not found')
    session.delete(tag)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
