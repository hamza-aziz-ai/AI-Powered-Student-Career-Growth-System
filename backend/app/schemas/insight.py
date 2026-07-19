import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CareerInsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    child_id: uuid.UUID
    model_name: str
    status: str
    result_text: str | None
    result_json: dict | None
    error_message: str | None
    generated_at: datetime | None
    created_at: datetime
