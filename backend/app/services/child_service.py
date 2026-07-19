import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child
from app.schemas.child import ChildCreate, ChildUpdate


async def create_child(db: AsyncSession, parent_id: uuid.UUID, data: ChildCreate) -> Child:
    child = Child(parent_id=parent_id, **data.model_dump())
    db.add(child)
    await db.commit()
    await db.refresh(child)
    return child


async def list_children(db: AsyncSession, parent_id: uuid.UUID) -> list[Child]:
    result = await db.scalars(select(Child).where(Child.parent_id == parent_id).order_by(Child.created_at))
    return list(result.all())


async def get_owned_child(db: AsyncSession, child_id: uuid.UUID, parent_id: uuid.UUID) -> Child | None:
    """Returns None both when the child doesn't exist and when it belongs to
    another parent — the router must not distinguish the two, so an
    unauthorized caller can't probe for which child IDs exist."""
    return await db.scalar(select(Child).where(Child.id == child_id, Child.parent_id == parent_id))


async def update_child(db: AsyncSession, child: Child, data: ChildUpdate) -> Child:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(child, field, value)
    await db.commit()
    await db.refresh(child)
    return child


async def delete_child(db: AsyncSession, child: Child) -> None:
    await db.delete(child)
    await db.commit()
