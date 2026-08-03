from collections.abc import Iterable, Mapping

from app.models.food import NutrientsPer100

NUTRIENT_FIELDS = tuple(NutrientsPer100.model_fields)
NET_CARB_DEDUCTIONS = ("fiber_g", "sugar_alcohol_g", "allulose_g")


def _nutrient_value(
    values: Mapping[str, float | int | None], field: str
) -> float | int | None:
    value = values.get(field)
    if field != "net_carbs_g" or value is not None:
        return value
    carbs = values.get("carbs_g")
    if carbs is None:
        return None
    deductions = sum(float(values.get(name) or 0) for name in NET_CARB_DEDUCTIONS)
    return max(float(carbs) - deductions, 0)


def scale_nutrients(
    values: Mapping[str, float | int | None], factor: float
) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for field in NUTRIENT_FIELDS:
        value = _nutrient_value(values, field)
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
