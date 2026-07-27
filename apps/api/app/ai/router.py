import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import LocalSafeTextProvider
from app.ai.schemas import CreditBalanceResponse, GenerationRequest, GenerationResponse
from app.ai.service import accept_generation, ensure_credit_account, generate_text
from app.auth.dependencies import current_user, get_db
from app.models import User

router = APIRouter(tags=["ai"])


@router.get("/credits", response_model=CreditBalanceResponse)
async def credits(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> CreditBalanceResponse:
    account = await ensure_credit_account(db, user.id)
    await db.commit()
    return CreditBalanceResponse(balance=account.balance)


@router.post(
    "/listings/{listing_id}/ai/text",
    response_model=GenerationResponse,
    status_code=201,
)
async def improve_listing_text(
    listing_id: uuid.UUID,
    data: GenerationRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerationResponse:
    return GenerationResponse.model_validate(await generate_text(
        db, listing_id, user.id, data.client_request_id, LocalSafeTextProvider()
    ))


@router.post(
    "/ai/generations/{generation_id}/accept",
    response_model=GenerationResponse,
)
async def accept_ai_generation(
    generation_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerationResponse:
    return GenerationResponse.model_validate(
        await accept_generation(db, generation_id, user.id)
    )
