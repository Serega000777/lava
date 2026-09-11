import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user, get_db
from app.interactions.schemas import InteractionResponse
from app.interactions.service import confirm_interaction, interaction_status
from app.models import User

router = APIRouter(tags=["interactions"])


@router.get(
    "/conversations/{conversation_id}/interaction",
    response_model=InteractionResponse,
)
async def get_interaction(
    conversation_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await interaction_status(db, conversation_id, user.id)


@router.put(
    "/conversations/{conversation_id}/interaction/completion",
    response_model=InteractionResponse,
)
async def complete_interaction(
    conversation_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    return await confirm_interaction(db, conversation_id, user.id)
