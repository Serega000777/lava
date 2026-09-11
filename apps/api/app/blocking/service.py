import uuid

from fastapi import HTTPException
from sqlalchemy import delete, exists, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserBlock


async def ensure_messaging_allowed(
    db: AsyncSession, first_user_id: uuid.UUID, second_user_id: uuid.UUID
) -> None:
    blocked = await db.scalar(
        select(
            exists().where(
                or_(
                    (UserBlock.blocker_id == first_user_id)
                    & (UserBlock.blocked_id == second_user_id),
                    (UserBlock.blocker_id == second_user_id)
                    & (UserBlock.blocked_id == first_user_id),
                )
            )
        )
    )
    if blocked:
        raise HTTPException(409, detail={"code": "messaging_blocked"})


async def block_user(
    db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID
) -> dict[str, object]:
    if blocker_id == blocked_id:
        raise HTTPException(409, detail={"code": "cannot_block_self"})
    target = await db.scalar(select(User).where(User.id == blocked_id, User.is_active.is_(True)))
    if target is None:
        raise HTTPException(404, detail={"code": "user_not_found"})
    await db.execute(
        insert(UserBlock)
        .values(blocker_id=blocker_id, blocked_id=blocked_id)
        .on_conflict_do_nothing(index_elements=["blocker_id", "blocked_id"])
    )
    await db.commit()
    created_at = await db.scalar(
        select(UserBlock.created_at).where(
            UserBlock.blocker_id == blocker_id,
            UserBlock.blocked_id == blocked_id,
        )
    )
    return {"user_id": target.id, "display_name": target.display_name, "created_at": created_at}


async def unblock_user(db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> None:
    await db.execute(
        delete(UserBlock).where(
            UserBlock.blocker_id == blocker_id,
            UserBlock.blocked_id == blocked_id,
        )
    )
    await db.commit()


async def list_blocked_users(
    db: AsyncSession, blocker_id: uuid.UUID, limit: int, offset: int
) -> list[dict[str, object]]:
    rows = (
        await db.execute(
            select(
                UserBlock.blocked_id.label("user_id"),
                User.display_name,
                UserBlock.created_at,
            )
            .join(User, User.id == UserBlock.blocked_id)
            .where(UserBlock.blocker_id == blocker_id)
            .order_by(UserBlock.created_at.desc(), UserBlock.blocked_id)
            .limit(limit)
            .offset(offset)
        )
    ).mappings().all()
    return [dict(row) for row in rows]
