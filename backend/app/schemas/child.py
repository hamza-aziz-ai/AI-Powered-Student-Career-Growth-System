import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

_CURRENT_YEAR = date.today().year
_MIN_BIRTH_YEAR = _CURRENT_YEAR - 19
_MAX_BIRTH_YEAR = _CURRENT_YEAR - 3

_Tag = Annotated[str, StringConstraints(min_length=1, max_length=200)]
_TagList = list[_Tag]


class ChildBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    birth_year: int = Field(ge=_MIN_BIRTH_YEAR, le=_MAX_BIRTH_YEAR)
    grade_level: str | None = Field(default=None, max_length=50)
    interests: _TagList = Field(default_factory=list, max_length=20)
    strengths: _TagList = Field(default_factory=list, max_length=20)
    favorite_subjects: _TagList | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=1000)


class ChildCreate(ChildBase):
    pass


class ChildUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    birth_year: int | None = Field(default=None, ge=_MIN_BIRTH_YEAR, le=_MAX_BIRTH_YEAR)
    grade_level: str | None = Field(default=None, max_length=50)
    interests: _TagList | None = Field(default=None, max_length=20)
    strengths: _TagList | None = Field(default=None, max_length=20)
    favorite_subjects: _TagList | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=1000)


class ChildRead(ChildBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
