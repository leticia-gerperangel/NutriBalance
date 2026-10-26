"""
etl/transform.py — Limpieza y normalización de nutrientes y alimentos extraídos desde la API USDA.
"""

import logging
 
logger = logging.getLogger(__name__)


# Constantes
# Límites VARCHAR definidos en db/schema.sql
FOOD_NAME_MAX_LEN = 150
FOOD_CATEGORY_MAX_LEN = 50
NUTRIENT_NAME_MAX_LEN = 100

# Unidades tal como las devuelve la USDA mapeadas a formato normalizado para la BD
UNIT_NORMALIZATION: dict[str, str] = {
    "G":    "g",
    "MG":   "mg",
    "UG":   "µg",
    "KCAL": "kcal",
    "KJ":   "kJ",
    "IU":   "IU",
}


# Funciones auxiliares

def _normalize_unit(unit: str) -> str:
    return UNIT_NORMALIZATION.get(unit.upper(), unit.lower())


# Transformaciones principales

def _transform_nutrient(raw: dict, nbr_mapping: dict[str, int]) -> dict | None:
    """
    Transforma un nutriente crudo de foodNutrients.
    Devuelve None si faltan campos obligatorios o el amount es inválido.
    """
    number  = str(raw.get("number", "")).strip()
    name    = raw.get("name", "").strip()
    unit    = raw.get("unitName", "").strip()
    amount  = raw.get("amount")
    usda_id = nbr_mapping.get(number)
 
    if not all([usda_id, name, unit]) or amount is None:
        return None
 
    amount = round(float(amount), 2)
    if amount < 0:
        return None
 
    return {
        "usda_id": usda_id,
        "name":    name[:NUTRIENT_NAME_MAX_LEN],
        "unit":    _normalize_unit(unit),
        "amount":  amount,
    }


def _transform_food(
    raw:          dict,
    nbr_mapping:  dict[str, int],
    category_map: dict[int, str],
    portion_map:  dict[int, float],
) -> dict | None:
    """
    Transforma un alimento crudo de /foods/list.
    Devuelve None si no tiene nombre o ningún nutriente válido.
    """
    name   = raw.get("description", "").strip()
    fdc_id = raw.get("fdcId")
 
    if not name:
        return None
 
    nutrients = [
        n for fn in raw.get("foodNutrients", [])
        if (n := _transform_nutrient(fn, nbr_mapping)) is not None
    ]
 
    if not nutrients:
        return None
 
    return {
        "fdc_id":    fdc_id,
        "name":      name[:FOOD_NAME_MAX_LEN],
        "source":    raw.get("dataType", "USDA"),
        "category":  category_map.get(fdc_id, "")[:FOOD_CATEGORY_MAX_LEN] or None,
        "serving_g": portion_map.get(fdc_id),
        "nutrients": nutrients,
    }


def transform_batch(
    raw_foods:    list[dict],
    nbr_mapping:  dict[str, int],
    category_map: dict[int, str],
    portion_map:  dict[int, float],
) -> tuple[list[dict], int]:
    """
    Transforma una lista de alimentos crudos.
    Devuelve (alimentos_válidos, cantidad_descartados).
    """
    valid     = []
    discarded = 0
 
    for raw in raw_foods:
        food = _transform_food(raw, nbr_mapping, category_map, portion_map)
        if food:
            valid.append(food)
        else:
            discarded += 1
 
    logger.debug("Batch transformado: %d válidos, %d descartados.", len(valid), discarded)
    return valid, discarded