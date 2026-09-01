import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.service import participant_conversation
from app.models import Conversation, Interaction, Review


async def _interaction(
    db: AsyncSession, conversation_id: uuid.UUID, *, lock: bool = False
) -> Interaction:
    query = select(Interaction).where(Interaction.conversation_id == conversation_id)
    if lock:
        query = query.with_for_update()
    interaction = await db.scalar(query)
    if interaction is None:
        raise RuntimeError("conversation interaction is missing")
    return interaction


async def _review_exists(
    db: AsyncSession, interaction_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    return bool(
        await db.scalar(
            select(
                exists().where(
                    Review.interaction_id == interaction_id,
                    Review.reviewer_id == user_id,
                )
            )
        )
    )


def interaction_response(
    conversation: Conversation,
    interaction: Interaction,
    user_id: uuid.UUID,
    review_created: bool,
) -> dict[str, object]:
    is_buyer = user_id == conversation.buyer_id
    my_confirmation = (
        interaction.buyer_confirmed_at if is_buyer else interaction.seller_confirmed_at
    )
    counterpart_confirmation = (
        interaction.seller_confirmed_at if is_buyer else interaction.buyer_confirmed_at
    )
    if interaction.completed_at is not None:
        status = "completed"
    elif interaction.contacted_at is not None:
        status = "contacted"
    else:
        status = "awaiting_contact"
    return {
        "id": interaction.id,
        "conversation_id": conversation.id,
        "status": status,
        "my_completion_confirmed": my_confirmation is not None,
        "counterpart_completion_confirmed": counterpart_confirmation is not None,
        "completed_at": interaction.completed_at,
        "can_review": interaction.completed_at is not None and not review_created,
        "review_created": review_created,
    }


async def interaction_status(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> dict[str, object]:
    conversation = await participant_conversation(db, conversation_id, user_id)
    interaction = await _interaction(db, conversation.id)
    reviewed = await _review_exists(db, interaction.id, user_id)
    return interaction_response(conversation, interaction, user_id, reviewed)


async def confirm_interaction(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> dict[str, object]:
    conversation = await participant_conversation(db, conversation_id, user_id)
    interaction = await _interaction(db, conversation.id, lock=True)
    if interaction.contacted_at is None:
        raise HTTPException(409, detail={"code": "interaction_not_started"})

    confirmed_at = datetime.now(UTC)
    if user_id == conversation.buyer_id and interaction.buyer_confirmed_at is None:
        interaction.buyer_confirmed_at = confirmed_at
    elif user_id == conversation.seller_id and interaction.seller_confirmed_at is None:
        interaction.seller_confirmed_at = confirmed_at
    if (
        interaction.buyer_confirmed_at is not None
        and interaction.seller_confirmed_at is not None
        and interaction.completed_at is None
    ):
        interaction.completed_at = confirmed_at
    await db.commit()
    reviewed = await _review_exists(db, interaction.id, user_id)
    return interaction_response(conversation, interaction, user_id, reviewed)
