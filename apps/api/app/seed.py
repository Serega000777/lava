import asyncio

from sqlalchemy.dialects.postgresql import insert

from app.db import session_factory
from app.models import Category

CATEGORIES = [
    {"slug": "cars", "name": "Автомобили"},
    {"slug": "goods", "name": "Товары"},
    {"slug": "services", "name": "Услуги"},
]


async def seed() -> None:
    async with session_factory() as session:
        statement = insert(Category).values(CATEGORIES).on_conflict_do_nothing(index_elements=["slug"])
        await session.execute(statement)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())

