import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.career_insight import CareerInsight
from app.models.child import Child
from app.services.ollama_client import OllamaResponseError, OllamaUnavailableError, generate_career_insight

settings = get_settings()
logger = get_logger(__name__)


class InsightGenerationFailedError(Exception):
    """Raised after the failure has already been persisted as a `failed` CareerInsight row."""

    def __init__(self, insight: CareerInsight):
        self.insight = insight
        super().__init__("Insight generation failed")


def _snapshot_profile(child: Child) -> dict:
    today = date.today()
    approx_age = today.year - child.birth_year
    return {
        "age": approx_age,
        "grade_level": child.grade_level,
        "interests": list(child.interests or []),
        "strengths": list(child.strengths or []),
        "favorite_subjects": list(child.favorite_subjects or []) if child.favorite_subjects else [],
        "notes": child.notes,
    }


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
    await db.refresh(insight)

    try:
        result = await generate_career_insight(profile_snapshot)
    except (OllamaUnavailableError, OllamaResponseError) as exc:
        logger.warning("insight generation failed for insight_id=%s: %s", insight.id, type(exc).__name__)
        insight.status = "failed"
        insight.error_message = "Insight generation is temporarily unavailable, please try again shortly."
        await db.commit()
        await db.refresh(insight)
        raise InsightGenerationFailedError(insight) from exc

    insight.status = "completed"
    insight.result_json = result
    insight.result_text = result.get("summary")
    insight.generated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(insight)
    return insight


async def list_insights_for_child(db: AsyncSession, child_id: uuid.UUID) -> list[CareerInsight]:
    result = await db.scalars(
        select(CareerInsight).where(CareerInsight.child_id == child_id).order_by(CareerInsight.created_at.desc())
    )
    return list(result.all())


async def get_insight(db: AsyncSession, child_id: uuid.UUID, insight_id: uuid.UUID) -> CareerInsight | None:
    return await db.scalar(
        select(CareerInsight).where(CareerInsight.id == insight_id, CareerInsight.child_id == child_id)
    )
