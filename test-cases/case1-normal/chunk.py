"""Small, well-documented utility. Normal-case test for the praas-agent reviewer."""
from typing import Iterator, Sequence, TypeVar

T = TypeVar("T")


def chunk(items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Yield successive chunks of at most `size` items from `items`."""
    if size <= 0:
        raise ValueError("size must be positive")
    for i in range(0, len(items), size):
        yield items[i : i + size]
