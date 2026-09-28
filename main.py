from __future__ import annotations

import secrets
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl, field_validator
from sqlalchemy import DateTime, Integer, String, create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{(BASE_DIR / 'urlshortener.db').as_posix()}"
SHORT_CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class URL(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    original_url: Mapped[str] = mapped_column(String, nullable=False)
    short_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    click_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)


class ShortenRequest(BaseModel):
    url: HttpUrl
    custom_code: str | None = None

    @field_validator("url")
    @classmethod
    def require_http_scheme(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme not in {"http", "https"}:
            raise ValueError("Only http:// and https:// URLs can be shortened.")
        return value

    @field_validator("custom_code", mode="before")
    @classmethod
    def validate_custom_code(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Custom short code must be text.")
        normalized = value.strip()
        if not normalized:
            return None
        if not 3 <= len(normalized) <= 30 or re.fullmatch(r"[A-Za-z0-9_-]+", normalized) is None:
            raise ValueError(
                "Custom short codes must be 3-30 characters and contain only letters, numbers, hyphens, or underscores."
            )
        return normalized


app = FastAPI(title="Tally URL Shortener", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def create_database_tables() -> None:
    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("urls")}
    if "click_count" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE urls ADD COLUMN click_count INTEGER NOT NULL DEFAULT 0"))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    message = "Enter a valid URL beginning with http:// or https://."
    for error in errors:
        if "custom_code" in error.get("loc", ()):
            message = (
                "Custom short codes must be 3-30 characters and contain only letters, numbers, hyphens, or underscores."
            )
            break
        if error.get("type") == "value_error" and "Only http://" in str(error.get("ctx", {}).get("error", "")):
            message = "Only http:// and https:// URLs can be shortened."
            break
    return JSONResponse(status_code=422, content={"detail": message})


@app.get("/", include_in_schema=False)
def homepage() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.post("/api/shorten")
def shorten_url(payload: ShortenRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, str | int | datetime]:
    if payload.custom_code:
        short_code = payload.custom_code
        existing = db.scalar(select(URL.id).where(URL.short_code == short_code))
        if existing is not None:
            raise HTTPException(status_code=409, detail="That custom short code is already in use.")
    else:
        while True:
            short_code = "".join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(7))
            existing = db.scalar(select(URL.id).where(URL.short_code == short_code))
            if existing is None:
                break

    url = URL(original_url=str(payload.url), short_code=short_code)
    db.add(url)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if payload.custom_code:
            raise HTTPException(status_code=409, detail="That custom short code is already in use.") from error
        raise
    db.refresh(url)

    return {
        "id": url.id,
        "original_url": url.original_url,
        "short_code": url.short_code,
        "short_url": str(request.base_url) + url.short_code,
        "created_at": url.created_at,
        "click_count": url.click_count,
    }


@app.get("/api/urls")
def list_urls(db: Session = Depends(get_db)) -> list[dict[str, str | int | datetime]]:
    urls = db.scalars(select(URL).order_by(URL.created_at.desc(), URL.id.desc())).all()
    return [
        {
            "id": url.id,
            "original_url": url.original_url,
            "short_code": url.short_code,
            "short_url": f"/{url.short_code}",
            "created_at": url.created_at,
            "click_count": url.click_count,
        }
        for url in urls
    ]


@app.get("/api/urls/{short_code}/stats")
def get_url_stats(short_code: str, db: Session = Depends(get_db)) -> dict[str, str | int | datetime]:
    url = db.scalar(select(URL).where(URL.short_code == short_code))
    if url is None:
        raise HTTPException(status_code=404, detail="That short URL does not exist.")
    return {
        "short_code": url.short_code,
        "original_url": url.original_url,
        "click_count": url.click_count,
        "created_at": url.created_at,
    }


@app.get("/{short_code}", include_in_schema=False)
def redirect_to_original(short_code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    url = db.scalar(select(URL).where(URL.short_code == short_code))
    if url is None:
        raise HTTPException(status_code=404, detail="That short URL does not exist.")
    url.click_count += 1
    db.commit()
    return RedirectResponse(url.original_url, status_code=307)