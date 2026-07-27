from typing import Protocol

from app.models import Listing
from app.search.schemas import SearchQuery


class SearchPort(Protocol):
    async def search(self, query: SearchQuery) -> tuple[list[Listing], int]: ...
