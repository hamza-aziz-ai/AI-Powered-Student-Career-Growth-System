from datetime import date

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

_VALID_BIRTH_YEAR = date.today().year - 10


async def _register(client: AsyncClient, email: str, password: str = "correcthorsebattery") -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test Parent"},
    )
    assert resp.status_code == 201, resp.text


def _child_payload(**overrides) -> dict:
    payload = {
        "first_name": "Alex",
        "birth_year": _VALID_BIRTH_YEAR,
        "grade_level": "5th grade",
        "interests": ["robotics", "drawing"],
        "strengths": ["curiosity"],
    }
    payload.update(overrides)
    return payload


async def test_create_and_get_child(client: AsyncClient, unique_email: str):
    await _register(client, unique_email)

    create_resp = await client.post("/api/children", json=_child_payload())
    assert create_resp.status_code == 201, create_resp.text
    child = create_resp.json()
    assert child["first_name"] == "Alex"
    assert child["birth_year"] == _VALID_BIRTH_YEAR

    get_resp = await client.get(f"/api/children/{child['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == child["id"]


async def test_list_children_scoped_to_parent(client: AsyncClient, unique_email: str):
    await _register(client, unique_email)
    await client.post("/api/children", json=_child_payload(first_name="Alex"))
    await client.post("/api/children", json=_child_payload(first_name="Sam"))

    list_resp = await client.get("/api/children")
    assert list_resp.status_code == 200
    names = {c["first_name"] for c in list_resp.json()}
    assert names == {"Alex", "Sam"}


async def test_update_child(client: AsyncClient, unique_email: str):
    await _register(client, unique_email)
    create_resp = await client.post("/api/children", json=_child_payload())
    child_id = create_resp.json()["id"]

    update_resp = await client.patch(f"/api/children/{child_id}", json={"grade_level": "6th grade"})
    assert update_resp.status_code == 200
    assert update_resp.json()["grade_level"] == "6th grade"
    assert update_resp.json()["first_name"] == "Alex"  # untouched fields preserved


async def test_delete_child(client: AsyncClient, unique_email: str):
    await _register(client, unique_email)
    create_resp = await client.post("/api/children", json=_child_payload())
    child_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/children/{child_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/children/{child_id}")
    assert get_resp.status_code == 404


async def test_child_endpoints_require_auth(client: AsyncClient):
    resp = await client.get("/api/children")
    assert resp.status_code == 401


async def test_cross_parent_access_is_denied(client: AsyncClient, unique_email: str):
    """The single most important authorization test in this app: one parent
    must never be able to read, edit, or delete another parent's child."""
    # Parent A creates a child.
    email_a = unique_email
    await _register(client, email_a)
    create_resp = await client.post("/api/children", json=_child_payload(first_name="ParentAsChild"))
    child_id = create_resp.json()["id"]

    # Parent B registers with a fresh session and tries to access Parent A's child.
    client.cookies.clear()
    email_b = f"other-{unique_email}"
    await _register(client, email_b)

    get_resp = await client.get(f"/api/children/{child_id}")
    assert get_resp.status_code == 404

    update_resp = await client.patch(f"/api/children/{child_id}", json={"grade_level": "10th grade"})
    assert update_resp.status_code == 404

    delete_resp = await client.delete(f"/api/children/{child_id}")
    assert delete_resp.status_code == 404

    list_resp = await client.get("/api/children")
    assert list_resp.status_code == 200
    assert list_resp.json() == []


async def test_birth_year_out_of_range_rejected(client: AsyncClient, unique_email: str):
    await _register(client, unique_email)
    resp = await client.post("/api/children", json=_child_payload(birth_year=1990))
    assert resp.status_code == 422
