import json

import httpx
import ollama

from app.core.config import get_settings

settings = get_settings()

_SYSTEM_PROMPT = (
    "You are a warm, encouraging career-exploration guide helping a parent think about "
    "possible future paths for their child. You are NOT a psychologist, counselor, or "
    "assessment tool — never provide a diagnosis, a definitive prediction, or clinical "
    "language. Speak directly to the parent. Base suggestions only on the interests, "
    "strengths, and context provided; do not invent facts about the child. Keep tone "
    "age-appropriate, positive, and exploratory rather than prescriptive.\n\n"
    'Respond ONLY with JSON matching this exact shape:\n'
    "{\n"
    '  "summary": "string, 2-3 sentences",\n'
    '  "career_suggestions": [\n'
    '    {"title": "string", "rationale": "string", "related_subjects": ["string"], '
    '"suggested_activities": ["string"]}\n'
    "  ],\n"
    '  "growth_areas": ["string"],\n'
    '  "disclaimer": "string, a brief note that this is exploratory guidance, not a '
    'professional assessment"\n'
    "}"
)


class OllamaUnavailableError(Exception):
    """Raised when Ollama can't be reached or times out."""


class OllamaResponseError(Exception):
    """Raised when Ollama responds but the content isn't usable (bad JSON, HTTP error)."""


def _build_user_prompt(profile: dict) -> str:
    """Builds the prompt sent to the (cloud-hosted) model. Deliberately excludes the
    child's first_name — the model only ever sees age band, grade, and tags, since this
    request leaves the machine when using a `*-cloud` Ollama model."""
    lines = [
        f"Child's age band: approximately {profile['age']} years old.",
        f"Grade level: {profile.get('grade_level') or 'not specified'}.",
        f"Interests: {', '.join(profile['interests']) or 'none specified'}.",
        f"Strengths: {', '.join(profile['strengths']) or 'none specified'}.",
    ]
    if profile.get("favorite_subjects"):
        lines.append(f"Favorite subjects: {', '.join(profile['favorite_subjects'])}.")
    if profile.get("notes"):
        lines.append(f"Additional context from parent: {profile['notes']}.")
    return "\n".join(lines)


async def generate_career_insight(profile: dict) -> dict:
    """Calls the local Ollama HTTP API and returns the parsed structured insight dict.

    Raises OllamaUnavailableError on connection/timeout issues, OllamaResponseError on
    a malformed or non-JSON response. Callers are responsible for persisting failure
    state — this function never touches the database.
    """
    client = ollama.AsyncClient(host=settings.ollama_base_url, timeout=settings.ollama_timeout_seconds)

    try:
        response = await client.chat(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(profile)},
            ],
            format="json",
            stream=False,
        )
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise OllamaUnavailableError(str(exc)) from exc
    except ollama.ResponseError as exc:
        raise OllamaResponseError(str(exc)) from exc

    message = response.get("message") or {}
    content = message.get("content")
    if not content:
        raise OllamaResponseError("Empty response from model")

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise OllamaResponseError(f"Model did not return valid JSON: {exc}") from exc
