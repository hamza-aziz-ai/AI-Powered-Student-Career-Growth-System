from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.children import get_owned_child_or_404
from app.models.child import Child
from app.models.user import User
from app.schemas.child import ChildCreate, ChildRead, ChildUpdate
from app.services import child_service

router = APIRouter(prefix="/api/children", tags=["children"])


@router.post("", response_model=ChildRead, status_code=status.HTTP_201_CREATED)
async def create_child(
    data: ChildCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await child_service.create_child(db, current_user.id, data)


@router.get("", response_model=list[ChildRead])
async def list_children(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await child_service.list_children(db, current_user.id)


@router.get("/{child_id}", response_model=ChildRead)
async def get_child(child: Child = Depends(get_owned_child_or_404)):
    return child


@router.patch("/{child_id}", response_model=ChildRead)
async def update_child(
    data: ChildUpdate,
    child: Child = Depends(get_owned_child_or_404),
    db: AsyncSession = Depends(get_db),
):
    return await child_service.update_child(db, child, data)


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_child(
    child: Child = Depends(get_owned_child_or_404),
    db: AsyncSession = Depends(get_db),
):
    await child_service.delete_child(db, child)
