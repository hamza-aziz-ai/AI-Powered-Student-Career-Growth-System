import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.dependencies.children import get_owned_child_or_404
from app.models.child import Child
from app.schemas.insight import CareerInsightRead
from app.services import insight_service

router = APIRouter(prefix="/api/children/{child_id}/insights", tags=["insights"])


@router.post("", response_model=CareerInsightRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def generate_insight(
    request: Request,
    child: Child = Depends(get_owned_child_or_404),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await insight_service.generate_insight_for_child(db, child)
    except insight_service.InsightGenerationFailedError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Insight generation is temporarily unavailable, please try again shortly.",
        )


@router.get("", response_model=list[CareerInsightRead])
async def list_insights(
    child: Child = Depends(get_owned_child_or_404),
    db: AsyncSession = Depends(get_db),
):
    return await insight_service.list_insights_for_child(db, child.id)


@router.get("/{insight_id}", response_model=CareerInsightRead)
async def get_insight(
    insight_id: uuid.UUID,
    child: Child = Depends(get_owned_child_or_404),
    db: AsyncSession = Depends(get_db),
):
    insight = await insight_service.get_insight(db, child.id, insight_id)
    if insight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found")
    return insight
