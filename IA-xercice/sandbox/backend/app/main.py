from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import GuestbookEntry
from app.schemas import GuestbookEntryCreate, GuestbookEntryRead

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/entries", response_model=list[GuestbookEntryRead])
def list_entries(db: Session = Depends(get_db)) -> list[GuestbookEntry]:
    stmt = select(GuestbookEntry).order_by(GuestbookEntry.created_at.desc(), GuestbookEntry.id.desc())
    return list(db.scalars(stmt))


@app.post("/entries", response_model=GuestbookEntryRead, status_code=status.HTTP_201_CREATED)
def create_entry(payload: GuestbookEntryCreate, db: Session = Depends(get_db)) -> GuestbookEntry:
    entry = GuestbookEntry(name=payload.name.strip(), message=payload.message.strip())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
