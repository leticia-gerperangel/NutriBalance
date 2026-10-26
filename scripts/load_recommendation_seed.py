"""
scripts/load_recommendation_seed.py — Carga la tabla recommendation desde data/dri_seed.csv.
Fuente: NIH/NCBI — NASEM Dietary Reference Intakes (RDA/AI) and Tolerable Upper Intake Levels (UL).
Ejecutar una sola vez tras init_db.py
"""

import logging
from pathlib import Path

import pandas as pd

from db.db import bulk_insert

logger = logging.getLogger(__name__)

SEED_PATH = Path("data/dri_seed.csv")

VALID_SEX       = {"male", "female", "other"}
VALID_CONDITION = {"none", "pregnancy", "lactation"}


def load_recommendations_from_csv() -> None:
    if not SEED_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró {SEED_PATH}.\n"
            "Asegúrate de que el archivo está en data/dri_seed.csv"
        )

    logger.info("Leyendo %s...", SEED_PATH)
    df = pd.read_csv(SEED_PATH, dtype=str)

    # Convertir tipos
    df["usda_id"]   = pd.to_numeric(df["usda_id"],   errors="coerce")
    df["age_min"]   = pd.to_numeric(df["age_min"],   errors="coerce")
    df["age_max"]   = pd.to_numeric(df["age_max"],   errors="coerce")
    df["dri_value"] = pd.to_numeric(df["dri_value"], errors="coerce")
    df["ul_value"]  = pd.to_numeric(df["ul_value"],  errors="coerce")

    # Descartar filas con campos obligatorios inválidos
    before = len(df)
    df = df.dropna(subset=["usda_id", "sex", "age_min", "age_max", "dri_value", "condition"])
    discarded = before - len(df)
    if discarded:
        logger.warning("  Descartadas %d filas con campos obligatorios vacíos.", discarded)

    # Validar valores de sex y condition
    invalid_sex = ~df["sex"].isin(VALID_SEX)
    if invalid_sex.any():
        raise ValueError(
            f"Valores de sex no válidos: {df.loc[invalid_sex, 'sex'].unique().tolist()}\n"
            f"Valores aceptados: {VALID_SEX}"
        )

    invalid_condition = ~df["condition"].isin(VALID_CONDITION)
    if invalid_condition.any():
        raise ValueError(
            f"Valores de condition no válidos: {df.loc[invalid_condition, 'condition'].unique().tolist()}\n"
            f"Valores aceptados: {VALID_CONDITION}"
        )

    # Validar que pregnancy y lactation solo aparecen en female
    invalid_condition_sex = (
        df["condition"].isin({"pregnancy", "lactation"}) & (df["sex"] != "female")
    )
    if invalid_condition_sex.any():
        raise ValueError(
            "Las condiciones 'pregnancy' y 'lactation' solo son válidas para sex='female'."
        )

    logger.info("  Total filas a cargar: %d", len(df))
    with_ul    = df["ul_value"].notna().sum()
    without_ul = df["ul_value"].isna().sum()
    logger.info("  With UL: %d | Without UL: %d", with_ul, without_ul)

    rows = list(zip(
        df["usda_id"].astype(int),
        df["sex"],
        df["age_min"].astype(int),
        df["age_max"].astype(int),
        df["condition"],
        df["dri_value"].astype(float),
        [None if pd.isna(v) else v for v in df["ul_value"]],
        df["source"],
    ))

    bulk_insert(
        table="recommendation",
        columns=["nutrient_id", "sex", "age_min", "age_max", "condition", "dri_value", "ul_value", "source"],
        rows=rows,
        conflict="DO NOTHING",
    )

    logger.info("%d recomendaciones cargadas en recommendation.", len(rows))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s — %(message)s",
    )
    load_recommendations_from_csv()