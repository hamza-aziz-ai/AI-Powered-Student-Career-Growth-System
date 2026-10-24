from datetime import date

from app.services.insight_service import _snapshot_profile
from app.services.ollama_client import _build_user_prompt
from app.models.child import Child


def _make_child(**overrides) -> Child:
    defaults = dict(
        first_name="Riley",
        birth_year=date.today().year - 10,
        grade_level="5th grade",
        interests=["robotics", "drawing"],
        strengths=["curiosity", "persistence"],
        favorite_subjects=["science"],
        notes="Loves building things with LEGO.",
    )
    defaults.update(overrides)
    return Child(**defaults)


def test_snapshot_profile_excludes_first_name():
    child = _make_child()
    snapshot = _snapshot_profile(child)

    assert "first_name" not in snapshot
    assert "name" not in snapshot
    assert snapshot["age"] == 10
    assert snapshot["grade_level"] == "5th grade"
    assert snapshot["interests"] == ["robotics", "drawing"]


def test_user_prompt_never_contains_child_name():
    child = _make_child(first_name="VeryUniqueNameXYZ")
    snapshot = _snapshot_profile(child)
    prompt = _build_user_prompt(snapshot)

    assert "VeryUniqueNameXYZ" not in prompt
    assert "age band" in prompt.lower()
    assert "robotics" in prompt


def test_notes_never_reach_snapshot_or_prompt():
    child = _make_child(notes="Private note mentioning VeryUniqueNoteXYZ")
    snapshot = _snapshot_profile(child)
    prompt = _build_user_prompt(snapshot)

    assert "notes" not in snapshot
    assert "VeryUniqueNoteXYZ" not in prompt


def test_user_prompt_handles_missing_optional_fields():
    child = _make_child(favorite_subjects=None, notes=None, grade_level=None, interests=[], strengths=[])
    snapshot = _snapshot_profile(child)
    prompt = _build_user_prompt(snapshot)

    assert "not specified" in prompt
