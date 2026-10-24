import asyncio
import json

import pytest

from app.services import ollama_client
from app.services.ollama_client import OllamaResponseError, OllamaUnavailableError, generate_career_insight

pytestmark = pytest.mark.asyncio

_PROFILE = {"age": 10, "grade_level": "5th grade", "interests": ["robotics"], "strengths": ["curiosity"]}

_VALID_RESULT = {
    "summary": "Shows strong curiosity.",
    "career_suggestions": [
        {
            "title": "Robotics Engineer",
            "rationale": "Enjoys building.",
            "related_subjects": ["science"],
            "suggested_activities": ["Join a robotics club"],
        }
    ],
    "growth_areas": ["Teamwork"],
    "disclaimer": "Exploratory guidance only.",
}


def _fake_client(*, content: str | None = None, raises: Exception | None = None):
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def chat(self, **kwargs):
            if raises is not None:
                raise raises
            return {"message": {"content": content}}

    return FakeAsyncClient


async def test_valid_result_is_returned(monkeypatch):
    monkeypatch.setattr(ollama_client.ollama, "AsyncClient", _fake_client(content=json.dumps(_VALID_RESULT)))
    assert await generate_career_insight(_PROFILE) == _VALID_RESULT


async def test_sdk_connection_error_maps_to_unavailable(monkeypatch):
    # ollama 0.6.x re-raises httpx.ConnectError as the builtin ConnectionError.
    monkeypatch.setattr(ollama_client.ollama, "AsyncClient", _fake_client(raises=ConnectionError("refused")))
    with pytest.raises(OllamaUnavailableError):
        await generate_career_insight(_PROFILE)


async def test_wall_clock_deadline_maps_to_unavailable(monkeypatch):
    class SlowAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def chat(self, **kwargs):
            await asyncio.sleep(5)

    monkeypatch.setattr(ollama_client.ollama, "AsyncClient", SlowAsyncClient)
    monkeypatch.setattr(ollama_client.settings, "ollama_timeout_seconds", 0.05)
    with pytest.raises(OllamaUnavailableError):
        await generate_career_insight(_PROFILE)


@pytest.mark.parametrize(
    "payload",
    [
        [],  # valid JSON, wrong top-level type
        {"summary": "Only a summary."},  # missing required keys
        {**_VALID_RESULT, "career_suggestions": []},  # no suggestions
        {**_VALID_RESULT, "career_suggestions": [{"title": "X"}]},  # incomplete nested item
        {**_VALID_RESULT, "growth_areas": "not a list"},
    ],
)
async def test_wrong_shape_is_rejected(monkeypatch, payload):
    monkeypatch.setattr(ollama_client.ollama, "AsyncClient", _fake_client(content=json.dumps(payload)))
    with pytest.raises(OllamaResponseError):
        await generate_career_insight(_PROFILE)


async def test_schema_error_message_does_not_echo_model_output(monkeypatch):
    secret = "ChildNameFromModelOutput"
    monkeypatch.setattr(ollama_client.ollama, "AsyncClient", _fake_client(content=json.dumps({"summary": secret})))
    with pytest.raises(OllamaResponseError) as exc_info:
        await generate_career_insight(_PROFILE)
    assert secret not in str(exc_info.value)
