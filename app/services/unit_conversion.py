from dataclasses import dataclass

WEIGHT_TO_GRAMS = {
    "g": 1.0,
    "kg": 1000.0,
    "oz": 28.3495,
    "lb": 453.592,
}

VOLUME_TO_ML = {
    "ml": 1.0,
    "l": 1000.0,
    "cup": 236.588,
    "tbsp": 14.787,
    "tsp": 4.929,
    "fl_oz": 29.574,
}

PORTION_UNITS = {"serving", "piece", "slice"}


@dataclass
class ConversionResult:
    grams: float
    approximate: bool


def convert_to_grams(
    amount: float,
    unit: str,
    density_g_per_ml: float | None = None,
    serving_quantity: float | None = None,
    serving_unit: str | None = None,
) -> ConversionResult:
    unit = unit.lower().strip()

    if unit in WEIGHT_TO_GRAMS:
        return ConversionResult(grams=amount * WEIGHT_TO_GRAMS[unit], approximate=False)

    if unit in VOLUME_TO_ML:
        ml = amount * VOLUME_TO_ML[unit]
        if density_g_per_ml is not None:
            return ConversionResult(grams=ml * density_g_per_ml, approximate=False)
        return ConversionResult(grams=ml * 1.0, approximate=True)

    if unit in PORTION_UNITS:
        if serving_quantity is None or serving_unit is None:
            raise ValueError(
                f"Cannot convert '{unit}' without serving_quantity and serving_unit on the food"
            )
        per_serving = convert_to_grams(serving_quantity, serving_unit, density_g_per_ml)
        return ConversionResult(
            grams=amount * per_serving.grams,
            approximate=per_serving.approximate,
        )

    raise ValueError(f"Unsupported unit: '{unit}'")
