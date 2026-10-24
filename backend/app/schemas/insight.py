import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CareerSuggestion(BaseModel):
    title: str = Field(min_length=1)
    rationale: str
    related_subjects: list[str]
    suggested_activities: list[str]


class InsightResult(BaseModel):
    """The JSON shape the model is told to return (see ollama_client._SYSTEM_PROMPT).
    Model output is validated against this before an insight is marked completed."""

    summary: str = Field(min_length=1)
    career_suggestions: list[CareerSuggestion] = Field(min_length=1)
    growth_areas: list[str]
    disclaimer: str


class CareerInsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    child_id: uuid.UUID
    model_name: str
    status: str
    result_text: str | None
    # Deliberately a plain dict: rows completed before output validation existed
    # may not match InsightResult, and history must still load.
    result_json: dict | None
    error_message: str | None
    generated_at: datetime | None
    created_at: datetime
