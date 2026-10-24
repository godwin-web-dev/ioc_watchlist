import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import IOC, Tag
from .normalize import IOC_TYPES, InvalidIOC, normalize
from .schemas import IOCCreate, IOCOut

UNSUPPORTED_MSG = (
    "Not a valid indicator. Supported types: IPv4 address, domain, URL (http/https/ftp), "
    "MD5, SHA-1 or SHA-256 hash. Defanged forms like hxxps://evil[.]com are accepted."
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="IOC Watchlist Manager", lifespan=lifespan)


def error(status: int, code: str, message: str, **extra) -> HTTPException:
    return HTTPException(status, detail={"code": code, "message": message, **extra})


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if p != "body")
    msg = first["msg"].removeprefix("Value error, ")
    return JSONResponse(
        status_code=422,
        content={"detail": {"code": "validation_error", "message": f"{field}: {msg}"}},
    )


def _get_or_create_tags(db: Session, names: list[str]) -> list[Tag]:
    if not names:
        return []
    existing = {t.name: t for t in db.scalars(select(Tag).where(Tag.name.in_(names)))}
    tags = []
    for name in names:
        tag = existing.get(name)
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
        tags.append(tag)
    return tags


def _find_by_value(db: Session, value: str) -> IOC | None:
    return db.scalar(select(IOC).where(IOC.value == value))


def _duplicate_error(existing: IOC) -> HTTPException:
    return error(
        409,
        "duplicate",
        f"This indicator already exists as entry #{existing.id} ({existing.type}: {existing.value}).",
        existing=IOCOut.model_validate(existing).model_dump(mode="json"),
    )


@app.post("/api/iocs", response_model=IOCOut, status_code=201)
def create_ioc(payload: IOCCreate, db: Session = Depends(get_db)):
    try:
        ioc_type, canonical = normalize(payload.value)
    except InvalidIOC as exc:
        raise error(422, "invalid_ioc", f"{exc} {UNSUPPORTED_MSG}") from None

    existing = _find_by_value(db, canonical)
    if existing:
        raise _duplicate_error(existing)

    ioc = IOC(
        type=ioc_type,
        value=canonical,
        raw_value=payload.value.strip(),
        note=(payload.note or "").strip() or None,
        tags=_get_or_create_tags(db, payload.tags),
    )
    db.add(ioc)
    try:
        db.commit()
    except IntegrityError:
        # Two concurrent requests passed the check above; the UNIQUE constraint caught it.
        db.rollback()
        existing = _find_by_value(db, canonical)
        if existing:
            raise _duplicate_error(existing) from None
        raise
    return ioc


@app.get("/api/iocs", response_model=list[IOCOut])
def list_iocs(
    tag: str | None = Query(default=None, description="Filter by tag name"),
    type: str | None = Query(default=None, description=f"One of: {', '.join(IOC_TYPES)}"),
    db: Session = Depends(get_db),
):
    if type is not None and type.lower() not in IOC_TYPES:
        raise error(422, "invalid_type", f"Unknown type '{type}'. Use one of: {', '.join(IOC_TYPES)}.")
    stmt = select(IOC).order_by(IOC.created_at.desc(), IOC.id.desc())
    if type:
        stmt = stmt.where(IOC.type == type.lower())
    if tag:
        stmt = stmt.where(IOC.tags.any(Tag.name == tag.strip().lower()))
    return db.scalars(stmt).all()


@app.get("/api/tags", response_model=list[str])
def list_tags(db: Session = Depends(get_db)):
    return list(db.scalars(select(Tag.name).order_by(Tag.name)))


@app.delete("/api/iocs/{ioc_id}", status_code=204)
def delete_ioc(ioc_id: int, db: Session = Depends(get_db)):
    ioc = db.get(IOC, ioc_id)
    if ioc is None:
        raise error(404, "not_found", f"IOC #{ioc_id} not found.")
    db.delete(ioc)
    db.flush()
    # Tidy up tags that no longer belong to any IOC so the tag filter stays accurate.
    for tag in db.scalars(select(Tag).where(~Tag.iocs.any())):
        db.delete(tag)
    db.commit()
    return Response(status_code=204)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve the built React app when present (single-container deployment).
_static = Path(os.getenv("STATIC_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="frontend")
