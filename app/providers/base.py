from typing import Protocol


class FoodNormalizer(Protocol):
    def __call__(self, raw: dict) -> dict: ...
