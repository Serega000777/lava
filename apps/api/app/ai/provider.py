from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TextSuggestion:
    title: str
    description: str


class TextProvider(Protocol):
    name: str
    model: str

    async def improve_listing(self, snapshot: dict[str, object]) -> TextSuggestion: ...


class LocalSafeTextProvider:
    name = "local"
    model = "deterministic-safe-v1"

    async def improve_listing(self, snapshot: dict[str, object]) -> TextSuggestion:
        title = " ".join(str(snapshot["title"]).split())
        description = " ".join(str(snapshot["description"]).split())
        if not description:
            description = f"{title}. Уточните состояние, комплектность и известные недостатки."
        return TextSuggestion(title=title, description=description)
