from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

ioc_tags = Table(
    "ioc_tags",
    Base.metadata,
    Column("ioc_id", ForeignKey("iocs.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class IOC(Base):
    __tablename__ = "iocs"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(10), index=True)
    # Canonical form; UNIQUE is what enforces "no duplicates", even under races.
    value: Mapped[str] = mapped_column(String(2100), unique=True)
    # What the analyst actually typed, kept for audit/display.
    raw_value: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary=ioc_tags, back_populates="iocs", order_by="Tag.name"
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    iocs: Mapped[list[IOC]] = relationship(secondary=ioc_tags, back_populates="tags")
