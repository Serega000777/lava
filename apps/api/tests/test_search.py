import pytest
from pydantic import ValidationError

from app.search.postgres import escape_like
from app.search.schemas import SearchQuery


def test_search_rejects_inverted_price_range() -> None:
    with pytest.raises(ValidationError):
        SearchQuery(price_min=100, price_max=50)


def test_search_rejects_unbounded_page_size() -> None:
    with pytest.raises(ValidationError):
        SearchQuery(limit=101)


def test_search_sort_is_allowlisted() -> None:
    with pytest.raises(ValidationError):
        SearchQuery(sort="DROP TABLE listings")


def test_search_treats_like_wildcards_as_literal_text() -> None:
    assert escape_like(r"100%_real\deal") == r"100\%\_real\\deal"
