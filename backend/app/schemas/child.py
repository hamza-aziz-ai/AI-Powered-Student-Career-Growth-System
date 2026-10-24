import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, field_validator

# Children are 3-19 years old at the time a profile is created or edited. The
# window is computed per request (not at import) so a long-running process
# doesn't keep last year's bounds after New Year.
_MIN_AGE = 3
_MAX_AGE = 19

_Tag = Annotated[str, StringConstraints(min_length=1, max_length=200)]
_TagList = list[_Tag]


def birth_year_bounds() -> tuple[int, int]:
    current_year = date.today().year
    return current_year - _MAX_AGE, current_year - _MIN_AGE


def _check_birth_year(value: int) -> int:
    min_year, max_year = birth_year_bounds()
    if not min_year <= value <= max_year:
        raise ValueError(f"birth_year must be between {min_year} and {max_year}")
    return value


_NewBirthYear = Annotated[int, AfterValidator(_check_birth_year)]


class ChildBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    birth_year: int
    grade_level: str | None = Field(default=None, max_length=50)
    interests: _TagList = Field(default_factory=list, max_length=20)
    strengths: _TagList = Field(default_factory=list, max_length=20)
    favorite_subjects: _TagList | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=1000)


class ChildCreate(ChildBase):
    birth_year: _NewBirthYear


class ChildUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    birth_year: _NewBirthYear | None = None
    grade_level: str | None = Field(default=None, max_length=50)
    interests: _TagList | None = Field(default=None, max_length=20)
    strengths: _TagList | None = Field(default=None, max_length=20)
    favorite_subjects: _TagList | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=1000)

    # These columns are NOT NULL: omitting them leaves the stored value alone, but an
    # explicit null must be rejected here rather than failing in the database.
    @field_validator("first_name", "birth_year", "interests", "strengths", mode="before")
    @classmethod
    def _reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("may be omitted but cannot be null")
        return value


class ChildRead(ChildBase):
    # No age-window check on read: a profile created years ago must stay readable.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
