import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import session_factory
from app.models import Category, CategoryAttribute

CATEGORIES = [
    {"slug": "cars", "name": "Автомобили"},
    {"slug": "goods", "name": "Товары"},
    {"slug": "services", "name": "Услуги"},
]

ATTRIBUTES = {
    "cars": [
        {"key": "make", "label": "Марка", "value_type": "text", "is_required": True},
        {"key": "year", "label": "Год выпуска", "value_type": "number", "is_required": True},
        {"key": "mileage", "label": "Пробег", "value_type": "number", "is_required": False},
    ],
    "goods": [
        {"key": "condition", "label": "Состояние", "value_type": "select", "is_required": True,
         "options": ["new", "used"]},
    ],
    "services": [
        {"key": "service_type", "label": "Вид услуги", "value_type": "text", "is_required": True},
    ],
}


async def seed() -> None:
    async with session_factory() as session:
        statement = insert(Category).values(CATEGORIES).on_conflict_do_nothing(index_elements=["slug"])
        await session.execute(statement)
        categories = (await session.scalars(select(Category))).all()
        for category in categories:
            for attribute in ATTRIBUTES.get(category.slug, []):
                await session.execute(
                    insert(CategoryAttribute)
                    .values(category_id=category.id, **attribute)
                    .on_conflict_do_nothing(index_elements=["category_id", "key"])
                )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
