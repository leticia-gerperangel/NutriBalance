"""
test/test_transform.py — Tests unitarios de etl/transform.py.

Cubre lógica pura de transformación: sin BD, sin API, sin ficheros.
Ejecutar con: pytest test/test_transform.py -v
"""

import pytest
from etl.transform import transform_batch, _transform_nutrient, _transform_food

# Fixtures compartidos

NBR_MAPPING = {"203": 1001, "204": 1002, "205": 1003}

VALID_NUTRIENT = {
    "number":   "203",
    "name":     "Protein",
    "unitName": "G",
    "amount":   25.5,
}

VALID_FOOD = {
    "fdcId":       12345,
    "description": "Chicken breast",
    "dataType":    "Foundation",
    "foodNutrients": [VALID_NUTRIENT],
}


# Trandsform nutrient

class TestTransformNutrient:

    def test_nutriente_valido(self):
        result = _transform_nutrient(VALID_NUTRIENT, NBR_MAPPING)
        assert result is not None
        assert result["usda_id"] == 1001
        assert result["name"]    == "Protein"
        assert result["unit"]    == "g"        # G normalizado a g
        assert result["amount"]  == 25.5

    def test_unidad_normalizada(self):
        raw = {**VALID_NUTRIENT, "unitName": "KCAL"}
        result = _transform_nutrient(raw, NBR_MAPPING)
        assert result["unit"] == "kcal"

    def test_amount_se_redondea_a_dos_decimales(self):
        raw = {**VALID_NUTRIENT, "amount": 25.678}
        result = _transform_nutrient(raw, NBR_MAPPING)
        assert result["amount"] == 25.68

    def test_number_sin_mapping_devuelve_none(self):
        raw = {**VALID_NUTRIENT, "number": "999"}  # no está en NBR_MAPPING
        assert _transform_nutrient(raw, NBR_MAPPING) is None

    def test_amount_none_devuelve_none(self):
        raw = {**VALID_NUTRIENT, "amount": None}
        assert _transform_nutrient(raw, NBR_MAPPING) is None

    def test_amount_negativo_devuelve_none(self):
        raw = {**VALID_NUTRIENT, "amount": -1.0}
        assert _transform_nutrient(raw, NBR_MAPPING) is None

    def test_amount_cero_es_valido(self):
        # Cero es un valor nutricional legítimo (ej: fibra en agua)
        raw = {**VALID_NUTRIENT, "amount": 0.0}
        result = _transform_nutrient(raw, NBR_MAPPING)
        assert result is not None
        assert result["amount"] == 0.0

    def test_nombre_vacio_devuelve_none(self):
        raw = {**VALID_NUTRIENT, "name": ""}
        assert _transform_nutrient(raw, NBR_MAPPING) is None

    def test_nombre_truncado_a_100_caracteres(self):
        raw = {**VALID_NUTRIENT, "name": "A" * 150}
        result = _transform_nutrient(raw, NBR_MAPPING)
        assert len(result["name"]) == 100


# Transform food

class TestTransformFood:

    CATEGORY_MAP = {12345: "Poultry Products"}
    PORTION_MAP  = {12345: 85.0}

    def test_alimento_valido(self):
        result = _transform_food(
            VALID_FOOD, NBR_MAPPING, self.CATEGORY_MAP, self.PORTION_MAP
        )
        assert result is not None
        assert result["fdc_id"]    == 12345
        assert result["name"]      == "Chicken breast"
        assert result["category"]  == "Poultry Products"
        assert result["serving_g"] == 85.0
        assert len(result["nutrients"]) == 1

    def test_sin_descripcion_devuelve_none(self):
        raw = {**VALID_FOOD, "description": ""}
        assert _transform_food(raw, NBR_MAPPING, {}, {}) is None

    def test_sin_nutrientes_validos_devuelve_none(self):
        raw = {**VALID_FOOD, "foodNutrients": []}
        assert _transform_food(raw, NBR_MAPPING, {}, {}) is None

    def test_category_none_si_no_hay_mapping(self):
        result = _transform_food(VALID_FOOD, NBR_MAPPING, {}, {})
        assert result["category"] is None

    def test_serving_g_none_si_no_hay_mapping(self):
        result = _transform_food(VALID_FOOD, NBR_MAPPING, {}, {})
        assert result["serving_g"] is None

    def test_nombre_truncado_a_150_caracteres(self):
        raw = {**VALID_FOOD, "description": "B" * 200}
        result = _transform_food(raw, NBR_MAPPING, {}, {})
        assert len(result["name"]) == 150

    def test_nutrientes_invalidos_son_filtrados(self):
        raw = {
            **VALID_FOOD,
            "foodNutrients": [
                VALID_NUTRIENT,
                {**VALID_NUTRIENT, "amount": None},   # inválido
                {**VALID_NUTRIENT, "number": "999"},   # sin mapping
            ]
        }
        result = _transform_food(raw, NBR_MAPPING, {}, {})
        assert len(result["nutrients"]) == 1  # solo el válido


# Transform batch

class TestTransformBatch:

    def test_batch_vacio(self):
        valid, discarded = transform_batch([], NBR_MAPPING, {}, {})
        assert valid     == []
        assert discarded == 0

    def test_cuenta_descartados_correctamente(self):
        sin_nombre = {**VALID_FOOD, "description": ""}
        valid, discarded = transform_batch(
            [VALID_FOOD, sin_nombre], NBR_MAPPING, {}, {}
        )
        assert len(valid) == 1
        assert discarded  == 1

    def test_todos_validos(self):
        food_2 = {**VALID_FOOD, "fdcId": 99999, "description": "Salmon"}
        valid, discarded = transform_batch(
            [VALID_FOOD, food_2], NBR_MAPPING, {}, {}
        )
        assert len(valid) == 2
        assert discarded  == 0