from datetime import date
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.services import insight_service
from app.services.ollama_client import OllamaUnavailableError

pytestmark = pytest.mark.asyncio

_VALID_BIRTH_YEAR = date.today().year - 10

_FAKE_RESULT = {
    "summary": "Riley shows strong curiosity and hands-on problem solving.",
    "career_suggestions": [
        {
            "title": "Robotics Engineer",
            "rationale": "Enjoys building and tinkering.",
            "related_subjects": ["science", "math"],
            "suggested_activities": ["Join a robotics club", "Try a beginner Arduino kit"],
        }
    ],
    "growth_areas": ["Teamwork on group projects"],
    "disclaimer": "This is exploratory guidance, not a professional assessment.",
}


async def _register(client: AsyncClient, email: str, password: str = "correcthorsebattery") -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test Parent"},
    )
    assert resp.status_code == 201, resp.text


async def _create_child(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/children",
        json={
            "first_name": "Riley",
            "birth_year": _VALID_BIRTH_YEAR,
            "grade_level": "5th grade",
            "interests": ["robotics"],
            "strengths": ["curiosity"],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_generate_insight_success(client: AsyncClient, unique_email: str, monkeypatch):
    mock_generate = AsyncMock(return_value=_FAKE_RESULT)
    monkeypatch.setattr(insight_service, "generate_career_insight", mock_generate)

    await _register(client, unique_email)
    child_id = await _create_child(client)

    resp = await client.post(f"/api/children/{child_id}/insights")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["result_json"] == _FAKE_RESULT
    assert body["result_text"] == _FAKE_RESULT["summary"]
    assert body["generated_at"] is not None

    mock_generate.assert_awaited_once()
    sent_profile = mock_generate.await_args.args[0]
    assert "first_name" not in sent_profile


async def test_generate_insight_ollama_unavailable_returns_503(client: AsyncClient, unique_email: str, monkeypatch):
    mock_generate = AsyncMock(side_effect=OllamaUnavailableError("connection refused"))
    monkeypatch.setattr(insight_service, "generate_career_insight", mock_generate)

    await _register(client, unique_email)
    child_id = await _create_child(client)

    resp = await client.post(f"/api/children/{child_id}/insights")
    assert resp.status_code == 503

    history = await client.get(f"/api/children/{child_id}/insights")
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["status"] == "failed"
    assert history.json()[0]["result_json"] is None


async def test_list_and_get_insight(client: AsyncClient, unique_email: str, monkeypatch):
    mock_generate = AsyncMock(return_value=_FAKE_RESULT)
    monkeypatch.setattr(insight_service, "generate_career_insight", mock_generate)

    await _register(client, unique_email)
    child_id = await _create_child(client)

    create_resp = await client.post(f"/api/children/{child_id}/insights")
    insight_id = create_resp.json()["id"]

    list_resp = await client.get(f"/api/children/{child_id}/insights")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    get_resp = await client.get(f"/api/children/{child_id}/insights/{insight_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == insight_id


async def test_insight_endpoints_require_auth(client: AsyncClient):
    resp = await client.post("/api/children/00000000-0000-0000-0000-000000000000/insights")
    assert resp.status_code == 401


async def test_cross_parent_cannot_generate_or_view_insights(client: AsyncClient, unique_email: str, monkeypatch):
    mock_generate = AsyncMock(return_value=_FAKE_RESULT)
    monkeypatch.setattr(insight_service, "generate_career_insight", mock_generate)

    await _register(client, unique_email)
    child_id = await _create_child(client)
    await client.post(f"/api/children/{child_id}/insights")

    client.cookies.clear()
    await _register(client, f"other-{unique_email}")

    gen_resp = await client.post(f"/api/children/{child_id}/insights")
    assert gen_resp.status_code == 404

    list_resp = await client.get(f"/api/children/{child_id}/insights")
    assert list_resp.status_code == 404
