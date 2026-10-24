import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.models.career_insight import CareerInsight
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


async def test_notes_are_not_sent_to_the_model(client: AsyncClient, unique_email: str, monkeypatch):
    mock_generate = AsyncMock(return_value=_FAKE_RESULT)
    monkeypatch.setattr(insight_service, "generate_career_insight", mock_generate)

    await _register(client, unique_email)
    child_id = await _create_child(client)
    await client.patch(f"/api/children/{child_id}", json={"notes": "Private parent note"})

    resp = await client.post(f"/api/children/{child_id}/insights")
    assert resp.status_code == 201
    sent_profile = mock_generate.await_args.args[0]
    assert "notes" not in sent_profile
    assert "Private parent note" not in str(sent_profile)


async def test_unexpected_generation_error_marks_row_failed(client: AsyncClient, unique_email: str, monkeypatch):
    # The exception text stands in for child data that must not leak into the response
    # or into an unhandled-exception traceback (the ASGI test transport would re-raise
    # an unhandled exception here instead of returning a response).
    leaky = RuntimeError("model said: Riley from Hillside Primary")
    monkeypatch.setattr(insight_service, "generate_career_insight", AsyncMock(side_effect=leaky))

    await _register(client, unique_email)
    child_id = await _create_child(client)

    resp = await client.post(f"/api/children/{child_id}/insights")
    assert resp.status_code == 500
    assert "Hillside" not in resp.text

    history = (await client.get(f"/api/children/{child_id}/insights")).json()
    assert [row["status"] for row in history] == ["failed"]


async def test_late_completion_does_not_overwrite_expired_row(
    client: AsyncClient, db_session, unique_email: str, monkeypatch
):
    async def expire_then_answer(profile):
        # Simulates stale-expiry failing the row while the model is still answering.
        await db_session.execute(
            update(CareerInsight).where(CareerInsight.status == "pending").values(status="failed")
        )
        await db_session.commit()
        return _FAKE_RESULT

    monkeypatch.setattr(insight_service, "generate_career_insight", expire_then_answer)

    await _register(client, unique_email)
    child_id = await _create_child(client)

    resp = await client.post(f"/api/children/{child_id}/insights")
    assert resp.status_code == 503

    history = (await client.get(f"/api/children/{child_id}/insights")).json()
    assert [row["status"] for row in history] == ["failed"]
    assert history[0]["result_json"] is None


async def test_stale_pending_rows_are_expired_on_read(client: AsyncClient, db_session, unique_email: str):
    await _register(client, unique_email)
    child_id = await _create_child(client)

    stale = CareerInsight(
        child_id=uuid.UUID(child_id),
        input_snapshot={},
        model_name="test",
        status="pending",
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    fresh = CareerInsight(child_id=uuid.UUID(child_id), input_snapshot={}, model_name="test", status="pending")
    db_session.add_all([stale, fresh])
    await db_session.commit()

    history = {row["id"]: row for row in (await client.get(f"/api/children/{child_id}/insights")).json()}
    assert history[str(stale.id)]["status"] == "failed"
    assert history[str(stale.id)]["error_message"]
    assert history[str(fresh.id)]["status"] == "pending"  # may still be running


async def test_generation_quota_is_per_parent_across_children(client: AsyncClient, unique_email: str, monkeypatch):
    monkeypatch.setattr(insight_service, "generate_career_insight", AsyncMock(return_value=_FAKE_RESULT))

    await _register(client, unique_email)
    first_child = await _create_child(client)
    second_child = await _create_child(client)

    for _ in range(10):
        assert (await client.post(f"/api/children/{first_child}/insights")).status_code == 201

    # A different child URL must not open a fresh 10/hour budget.
    resp = await client.post(f"/api/children/{second_child}/insights")
    assert resp.status_code == 429
