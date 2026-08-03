from collections.abc import Iterable, Mapping

from app.models.food import NutrientsPer100

NUTRIENT_FIELDS = tuple(NutrientsPer100.model_fields)


def scale_nutrients(
    values: Mapping[str, float | int | None], factor: float
) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for field in NUTRIENT_FIELDS:
        value = values.get(field)
        result[field] = None if value is None else round(float(value) * factor, 2)
    return result


def sum_nutrients(
    items: Iterable[Mapping[str, float | int | None]], *, empty_is_zero: bool = False
) -> dict[str, float | None]:
    materialized = tuple(items)
    result: dict[str, float | None] = {}
    for field in NUTRIENT_FIELDS:
        values = [
            float(item[field]) for item in materialized if item.get(field) is not None
        ]
        if values:
            result[field] = round(sum(values), 2)
        elif not materialized and empty_is_zero:
            result[field] = 0.0
        else:
            result[field] = None
    return result
