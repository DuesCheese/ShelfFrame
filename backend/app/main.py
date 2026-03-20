from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.activity import router as activity_router
from app.api.routes.health import router as health_router
from app.api.routes.scan import router as scan_router
from app.api.routes.settings import router as settings_router
from app.api.routes.tags import router as tags_router
from app.api.routes.works import router as works_router
from app.core.config import settings
from app.db import Base, SessionLocal, engine
from app.services.media_roots import bootstrap_media_root

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        bootstrap_media_root(session)


app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(activity_router, prefix=settings.api_prefix)
app.include_router(settings_router, prefix=settings.api_prefix)
app.include_router(scan_router, prefix=settings.api_prefix)
app.include_router(tags_router, prefix=settings.api_prefix)
app.include_router(works_router, prefix=settings.api_prefix)
