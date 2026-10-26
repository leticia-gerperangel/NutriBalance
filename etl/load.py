"""
etl/load.py — Inserción de alimentos y nutrientes en PostgreSQL.
"""
 
import logging
 
from db.db import bulk_insert, fetch_one, get_db
 
logger = logging.getLogger(__name__)


# Nutrientes

def load_nutrients(nutrients: list[dict]) -> dict[int, int]:
    """
    Inserta los nutrientes únicos en la tabla nutrient.
    Devuelve {usda_id: nutrient.id} para usarlo al insertar food_nutrient.
    """
    unique_nutrients = {n["usda_id"]: n for n in nutrients}
 
    rows = [
        (usda_id, n["name"], n["unit"])
        for usda_id, n in unique_nutrients.items()
    ]
 
    bulk_insert(
        table="nutrient",
        columns=["usda_id", "name", "unit"],
        rows=rows,
        conflict="(usda_id) DO NOTHING",
    )
 
    usda_ids = list(unique_nutrients.keys())
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, usda_id FROM nutrient WHERE usda_id = ANY(%s)",
                (usda_ids,),
            )
            return {row[1]: row[0] for row in cur.fetchall()}


# Alimentos

def load_food(food: dict, nutrient_map: dict[int, int]) -> bool:
    """
    Inserta un alimento y sus relaciones en food_nutrient.
    Devuelve True si se insertó, False si ya existía (duplicado).
    """
    already_exists = fetch_one(
        "SELECT id FROM food WHERE fdc_id = %s",
        (food["fdc_id"],),
    )
    if already_exists:
        return False
 
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO food (fdc_id, name, source, category, serving_g)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    food["fdc_id"],
                    food["name"],
                    food["source"],
                    food["category"],
                    food.get("serving_g"),
                ),
            )
            food_id = cur.fetchone()[0]
 
    food_nutrient_rows = [
        (food_id, nutrient_map[n["usda_id"]], n["amount"])
        for n in food["nutrients"]
        if n["usda_id"] in nutrient_map
    ]
 
    if food_nutrient_rows:
        bulk_insert(
            table="food_nutrient",
            columns=["food_id", "nutrient_id", "amount"],
            rows=food_nutrient_rows,
            conflict="(food_id, nutrient_id) DO NOTHING",
        )
 
    logger.debug("Alimento insertado: fdc_id=%d, nutrientes=%d", food["fdc_id"], len(food_nutrient_rows))
    return True