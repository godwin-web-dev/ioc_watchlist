import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

TAG_RE = re.compile(r"[a-z0-9][a-z0-9_.:-]{0,49}")


class IOCCreate(BaseModel):
    value: str = Field(max_length=2100)
    note: str | None = Field(default=None, max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, tags: list[str]) -> list[str]:
        seen: dict[str, None] = {}
        for t in tags:
            name = t.strip().lower()
            if not name:
                continue
            if not TAG_RE.fullmatch(name):
                raise ValueError(
                    f"Invalid tag '{t}'. Use letters, digits, '_', '-', '.', ':' (max 50 chars)."
                )
            seen[name] = None
        return list(seen)


class IOCOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    value: str
    raw_value: str
    note: str | None
    tags: list[str]
    created_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def tag_names(cls, v):
        return sorted(t.name if hasattr(t, "name") else t for t in v)
