"""
etl/pipeline.py — Orquestación del ETL completo de NutriBalance.
"""

import logging
from pathlib import Path

import pandas as pd

from db.db import fetch_all
from etl.extract import fetch_all_foods
from etl.load import load_food, load_nutrients
from etl.transform import transform_batch

logger = logging.getLogger(__name__)

BATCH_SIZE = 200


# Prerequisito del ETL
def _load_nbr_mapping() -> dict[str, int]:
    """Devuelve {nutrient_nbr: usda_id} desde nutrient_catalog en BD."""
    rows = fetch_all("SELECT usda_id, nutrient_nbr FROM nutrient_catalog")
    return {row["nutrient_nbr"]: row["usda_id"] for row in rows}


# Enriquecimiento de alimentos con categoría y porción de referencia
def _load_category_mapping() -> dict[int, str]:
    """
    Devuelve {fdc_id: category_description} cruzando:
      - data/foundation/food.csv  (fdc_id, food_category_id)
      - data/legacy/l_food.csv    (fdc_id, food_category_id)
      - data/food_category.csv    (id, description)
    """
    category_df = pd.read_csv(Path("data/food_category.csv"), dtype={"id": int})
    category_map = dict(zip(category_df["id"], category_df["description"].str.strip()))
 
    foundation = pd.read_csv(Path("data/foundation/food.csv"))
    foundation = foundation[foundation["data_type"] == "foundation_food"][
        ["fdc_id", "food_category_id"]
    ].dropna()
 
    legacy = pd.read_csv(Path("data/legacy/l_food.csv"))[
        ["fdc_id", "food_category_id"]
    ].dropna()
 
    combined = pd.concat([foundation, legacy], ignore_index=True)
    combined["fdc_id"]           = combined["fdc_id"].astype(int)
    combined["food_category_id"] = combined["food_category_id"].astype(int)
    combined["category"]         = combined["food_category_id"].map(category_map)
 
    return dict(zip(combined["fdc_id"], combined["category"].fillna("")))


def _load_portion_mapping() -> dict[int, float]:
    """
    Devuelve {fdc_id: gram_weight} tomando la porción de referencia (menor seq_num) de Foundation y SR Legacy.
    """
    def _reference_portion(df: pd.DataFrame) -> pd.DataFrame:
        df = df.dropna(subset=["fdc_id", "gram_weight"]).copy()
        df["fdc_id"] = df["fdc_id"].astype(int)
 
        with_seq    = df.dropna(subset=["seq_num"])
        without_seq = df[df["seq_num"].isna()]
 
        parts = []
        if not with_seq.empty:
            parts.append(
                with_seq.sort_values("seq_num")
                .groupby("fdc_id", as_index=False)
                .first()[["fdc_id", "gram_weight"]]
            )
        if not without_seq.empty:
            parts.append(
                without_seq.groupby("fdc_id", as_index=False)
                .first()[["fdc_id", "gram_weight"]]
            )
 
        return (
            pd.concat(parts, ignore_index=True)
            .drop_duplicates(subset=["fdc_id"], keep="first")
        )
 
    foundation = _reference_portion(
        pd.read_csv(Path("data/foundation/food_portion.csv"))
    )
    legacy = _reference_portion(
        pd.read_csv(Path("data/legacy/l_food_portion.csv"))
    )
 
    combined = (
        pd.concat([foundation, legacy], ignore_index=True)
        .drop_duplicates(subset=["fdc_id"], keep="first")
    )
    return dict(zip(combined["fdc_id"].astype(int), combined["gram_weight"].astype(float)))


# Orquestación

def run(max_pages: int | None = None) -> None:
    """
    Ejecuta el ETL completo: extrae, transforma y carga en PostgreSQL.

    Args:
        max_pages: límite de páginas por data_type en la API.
                   None = producción (descarga todo).
                   2 ó 3 = prueba rápida.
    """
    logger.info("=" * 50)
    logger.info("NutriBalance ETL — inicio")
    logger.info("=" * 50)

    logger.info("Cargando mappings de enriquecimiento...")
    nbr_mapping  = _load_nbr_mapping()
    category_map = _load_category_mapping()
    portion_map  = _load_portion_mapping()
    logger.info(
        "  nbr_mapping=%d | category_map=%d | portion_map=%d",
        len(nbr_mapping), len(category_map), len(portion_map),
    )

    logger.info("[1/2] Extrayendo alimentos de la API USDA...")
    all_foods = fetch_all_foods(max_pages=max_pages)
    logger.info("  Total alimentos únicos extraídos: %d", len(all_foods))

    logger.info("[2/2] Transformando y cargando en BD...")
    nutrient_map = {}
    insertados = 0
    omitidos   = 0
    descartados = 0

    for i in range(0, len(all_foods), BATCH_SIZE):
        batch = all_foods[i : i + BATCH_SIZE]

        transformed, disc = transform_batch(batch, nbr_mapping, category_map, portion_map)
        descartados += disc

        all_nutrients = [n for food in transformed for n in food["nutrients"]]
        batch_map = load_nutrients(all_nutrients)
        nutrient_map.update(batch_map)

        for food in transformed:
            if load_food(food, nutrient_map):
                insertados += 1
            else:
                omitidos += 1

        logger.info(
            "  Batch %d/%d — insertados: %d | omitidos: %d | descartados: %d",
            i // BATCH_SIZE + 1,
            -(-len(all_foods) // BATCH_SIZE),  # ceil division
            insertados, omitidos, descartados,
        )

    logger.info("=" * 50)
    logger.info("ETL completado:")
    logger.info("  Insertados:  %d", insertados)
    logger.info("  Omitidos:    %d", omitidos)
    logger.info("  Descartados: %d", descartados)
    logger.info("  Nutrientes:  %d", len(nutrient_map))
    logger.info("=" * 50)