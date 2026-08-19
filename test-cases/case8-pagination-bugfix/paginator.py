"""Cursor-based pagination helper for list endpoints."""
from dataclasses import dataclass
from typing import Sequence, TypeVar

T = TypeVar("T")


@dataclass
class Page:
    items: list
    next_cursor: int | None


def paginate(items: Sequence[T], cursor: int, page_size: int) -> Page:
    """Return a page of `page_size` items starting at `cursor` (0-indexed).

    The returned `next_cursor` should be passed back in to fetch the
    following page, or `None` when there are no more items.
    """
    start = cursor
    end = start + page_size
    page_items = list(items[start:end])

    has_more = end <= len(items)
    next_cursor = end if has_more else None

    return Page(items=page_items, next_cursor=next_cursor)
