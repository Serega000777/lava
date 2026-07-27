import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import TextProvider
from app.models import AiGeneration, CreditAccount, CreditLedgerEntry, Listing

WELCOME_CREDITS = 10
TEXT_CREDIT_COST = 1
PROMPT_VERSION = "listing-text-v1"


async def owned_draft(db: AsyncSession, listing_id: uuid.UUID, user_id: uuid.UUID) -> Listing:
    listing = await db.scalar(
        select(Listing).where(Listing.id == listing_id, Listing.owner_id == user_id)
    )
    if listing is None:
        raise HTTPException(404, detail={"code": "listing_not_found"})
    if listing.status != "draft":
        raise HTTPException(409, detail={"code": "listing_not_draft"})
    return listing


async def ensure_credit_account(db: AsyncSession, user_id: uuid.UUID) -> CreditAccount:
    created = await db.scalar(
        insert(CreditAccount)
        .values(user_id=user_id, balance=WELCOME_CREDITS)
        .on_conflict_do_nothing(index_elements=["user_id"])
        .returning(CreditAccount.user_id)
    )
    if created:
        db.add(CreditLedgerEntry(
            user_id=user_id,
            kind="welcome_grant",
            amount=WELCOME_CREDITS,
            balance_after=WELCOME_CREDITS,
            reference_id=user_id,
        ))
    account = await db.scalar(
        select(CreditAccount).where(CreditAccount.user_id == user_id).with_for_update()
    )
    if account is None:
        raise RuntimeError("credit account creation failed")
    return account


async def generate_text(
    db: AsyncSession,
    listing_id: uuid.UUID,
    user_id: uuid.UUID,
    client_request_id: uuid.UUID,
    provider: TextProvider,
) -> AiGeneration:
    listing = await owned_draft(db, listing_id, user_id)
    snapshot = {
        "title": listing.title,
        "description": listing.description,
        "category_id": str(listing.category_id),
        "attributes": listing.attributes,
    }
    generation_id = uuid.uuid4()
    created = await db.scalar(
        insert(AiGeneration)
        .values(
            id=generation_id,
            user_id=user_id,
            listing_id=listing.id,
            client_request_id=client_request_id,
            status="pending",
            provider=provider.name,
            model=provider.model,
            prompt_version=PROMPT_VERSION,
            input_snapshot=snapshot,
            credit_cost=TEXT_CREDIT_COST,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "client_request_id"])
        .returning(AiGeneration.id)
    )
    if created is None:
        existing = await db.scalar(
            select(AiGeneration).where(
                AiGeneration.user_id == user_id,
                AiGeneration.client_request_id == client_request_id,
            )
        )
        if existing is None:
            raise RuntimeError("generation idempotency lookup failed")
        return existing

    account = await ensure_credit_account(db, user_id)
    if account.balance < TEXT_CREDIT_COST:
        await db.rollback()
        raise HTTPException(402, detail={"code": "insufficient_credits"})
    account.balance -= TEXT_CREDIT_COST
    db.add(CreditLedgerEntry(
        user_id=user_id,
        kind="ai_text_debit",
        amount=-TEXT_CREDIT_COST,
        balance_after=account.balance,
        reference_id=generation_id,
    ))
    await db.commit()

    generation = await db.scalar(select(AiGeneration).where(AiGeneration.id == generation_id))
    if generation is None:
        raise RuntimeError("generation disappeared")
    try:
        suggestion = await provider.improve_listing(snapshot)
        if not (
            3 <= len(suggestion.title) <= 140
            and len(suggestion.description) <= 10_000
        ):
            raise ValueError("provider output violates listing limits")
        generation.output = {
            "title": suggestion.title,
            "description": suggestion.description,
        }
        generation.status = "completed"
        await db.commit()
    except Exception:
        account = await db.scalar(
            select(CreditAccount).where(CreditAccount.user_id == user_id).with_for_update()
        )
        generation = await db.scalar(select(AiGeneration).where(AiGeneration.id == generation_id))
        if account is not None and generation is not None:
            account.balance += TEXT_CREDIT_COST
            generation.status = "failed"
            generation.error_code = "provider_error"
            db.add(CreditLedgerEntry(
                user_id=user_id,
                kind="ai_text_refund",
                amount=TEXT_CREDIT_COST,
                balance_after=account.balance,
                reference_id=generation_id,
            ))
            await db.commit()
        raise HTTPException(503, detail={"code": "ai_provider_unavailable"})
    return generation


async def accept_generation(
    db: AsyncSession, generation_id: uuid.UUID, user_id: uuid.UUID
) -> AiGeneration:
    generation = await db.scalar(
        select(AiGeneration).where(
            AiGeneration.id == generation_id,
            AiGeneration.user_id == user_id,
        )
    )
    if generation is None:
        raise HTTPException(404, detail={"code": "generation_not_found"})
    if generation.status == "accepted":
        return generation
    if generation.status != "completed" or generation.output is None:
        raise HTTPException(409, detail={"code": "generation_not_ready"})
    listing = await owned_draft(db, generation.listing_id, user_id)
    title = str(generation.output["title"])
    description = str(generation.output["description"])
    if not (3 <= len(title) <= 140 and len(description) <= 10_000):
        raise HTTPException(409, detail={"code": "generation_output_invalid"})
    listing.title = title
    listing.description = description
    listing.ai_generated_fields = ["title", "description"]
    generation.status = "accepted"
    generation.accepted_at = datetime.now(UTC)
    await db.commit()
    return generation
