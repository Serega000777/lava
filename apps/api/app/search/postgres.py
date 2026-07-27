from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Listing
from app.search.schemas import SearchQuery


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class PostgresListingSearch:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(self, query: SearchQuery) -> tuple[list[Listing], int]:
        filters = [Listing.status == "active"]
        if query.category_id:
            filters.append(Listing.category_id == query.category_id)
        if query.city:
            filters.append(func.lower(Listing.city) == query.city.lower())
        if query.price_min is not None:
            filters.append(Listing.price >= query.price_min)
        if query.price_max is not None:
            filters.append(Listing.price <= query.price_max)

        relevance = None
        if query.q.strip():
            needle = query.q.strip()
            like_needle = escape_like(needle)
            filters.append(or_(
                Listing.title.ilike(f"%{like_needle}%", escape="\\"),
                Listing.description.ilike(f"%{like_needle}%", escape="\\"),
            ))
            relevance = (
                case((func.lower(Listing.title) == needle.lower(), 3.0), else_=0.0)
                + func.similarity(Listing.title, needle) * 2
                + func.similarity(Listing.description, needle)
            )

        order = {
            "newest": [Listing.created_at.desc(), Listing.id],
            "price_asc": [Listing.price.asc().nullslast(), Listing.id],
            "price_desc": [Listing.price.desc().nullslast(), Listing.id],
        }.get(query.sort)
        if query.sort == "relevance":
            order = [relevance.desc(), Listing.created_at.desc()] if relevance is not None else [
                Listing.created_at.desc(), Listing.id
            ]

        total = await self.db.scalar(select(func.count()).select_from(Listing).where(*filters))
        items = (await self.db.scalars(
            select(Listing).where(*filters).order_by(*order).limit(query.limit).offset(query.offset)
        )).all()
        return list(items), int(total or 0)
