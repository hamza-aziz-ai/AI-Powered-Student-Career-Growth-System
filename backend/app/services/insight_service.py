import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.career_insight import CareerInsight
from app.models.child import Child
from app.services.ollama_client import OllamaResponseError, OllamaUnavailableError, generate_career_insight

settings = get_settings()
logger = get_logger(__name__)

_FAILURE_MESSAGE = "Insight generation is temporarily unavailable, please try again shortly."
_INTERRUPTED_MESSAGE = "This insight didn't finish generating. Please try again."


class InsightGenerationFailedError(Exception):
    """Raised after the failure has been persisted as a `failed` row (best effort).

    `unexpected` distinguishes a bug or infrastructure fault (HTTP 500) from the model
    service being unavailable or returning unusable output (HTTP 503). The original
    exception is deliberately not chained: its message could carry child data and
    would otherwise be printed in the server's traceback log."""

    def __init__(self, insight_id: uuid.UUID, *, unexpected: bool = False):
        self.insight_id = insight_id
        self.unexpected = unexpected
        super().__init__("Insight generation failed")


def _snapshot_profile(child: Child) -> dict:
    """What is sent to the model and stored as input_snapshot. Excludes first_name
    and the parent's free-text notes, which stay on the child profile only."""
    today = date.today()
    approx_age = today.year - child.birth_year
    return {
        "age": approx_age,
        "grade_level": child.grade_level,
        "interests": list(child.interests or []),
        "strengths": list(child.strengths or []),
        "favorite_subjects": list(child.favorite_subjects or []) if child.favorite_subjects else [],
    }


async def _finish_pending(db: AsyncSession, insight_id: uuid.UUID, **values) -> bool:
    """Move a row out of `pending` only if it is still pending, so a completion can't
    overwrite a row that stale-expiry already failed, and vice versa."""
    result = await db.execute(
        update(CareerInsight)
        .where(CareerInsight.id == insight_id, CareerInsight.status == "pending")
        .values(**values)
    )
    await db.commit()
    return result.rowcount == 1


async def _mark_failed(db: AsyncSession, insight_id: uuid.UUID) -> None:
    try:
        await db.rollback()
        await _finish_pending(db, insight_id, status="failed", error_message=_FAILURE_MESSAGE)
    except Exception as exc:
        # Persisting the failure must not mask the original failure; stale-expiry on
        # read will fail the row later if this didn't.
        logger.error("could not mark insight_id=%s failed: %s", insight_id, type(exc).__name__)


async def generate_insight_for_child(db: AsyncSession, child: Child) -> CareerInsight:
    profile_snapshot = _snapshot_profile(child)

    insight = CareerInsight(
        child_id=child.id,
        input_snapshot=profile_snapshot,
        model_name=settings.ollama_model,
        status="pending",
    )
    db.add(insight)
    await db.commit()
    insight_id = insight.id

    try:
        result = await generate_career_insight(profile_snapshot)
        completed = await _finish_pending(
            db,
            insight_id,
            status="completed",
            result_json=result,
            result_text=result.get("summary"),
            generated_at=datetime.now(timezone.utc),
        )
    except (OllamaUnavailableError, OllamaResponseError) as exc:
        logger.warning("insight generation failed for insight_id=%s: %s", insight_id, type(exc).__name__)
        await _mark_failed(db, insight_id)
        raise InsightGenerationFailedError(insight_id) from None
    except Exception as exc:
        # Log only the class name: exception text could carry model output.
        logger.error("unexpected insight generation error for insight_id=%s: %s", insight_id, type(exc).__name__)
        await _mark_failed(db, insight_id)
        raise InsightGenerationFailedError(insight_id, unexpected=True) from None

    if not completed:
        # Expired as interrupted while the model was still answering; keep that outcome.
        raise InsightGenerationFailedError(insight_id)

    await db.refresh(insight)
    return insight


async def _expire_stale_pending(db: AsyncSession, child_id: uuid.UUID) -> None:
    """Lazy recovery on read, not a periodic job. generate_career_insight enforces a
    wall-clock deadline of ollama_timeout_seconds, so a row still pending after twice
    that was interrupted (process restart, cancelled request) and will never complete."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.ollama_timeout_seconds * 2)
    result = await db.execute(
        update(CareerInsight)
        .where(
            CareerInsight.child_id == child_id,
            CareerInsight.status == "pending",
            CareerInsight.created_at < cutoff,
        )
        .values(status="failed", error_message=_INTERRUPTED_MESSAGE)
    )
    if result.rowcount:
        await db.commit()


async def list_insights_for_child(db: AsyncSession, child_id: uuid.UUID) -> list[CareerInsight]:
    await _expire_stale_pending(db, child_id)
    result = await db.scalars(
        select(CareerInsight).where(CareerInsight.child_id == child_id).order_by(CareerInsight.created_at.desc())
    )
    return list(result.all())


async def get_insight(db: AsyncSession, child_id: uuid.UUID, insight_id: uuid.UUID) -> CareerInsight | None:
    await _expire_stale_pending(db, child_id)
    return await db.scalar(
        select(CareerInsight).where(CareerInsight.id == insight_id, CareerInsight.child_id == child_id)
    )
