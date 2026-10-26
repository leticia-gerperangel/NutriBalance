"""
scripts/load_nutrient_seed.py — Carga nutrient_catalog desde data/nutrient.csv.
 
Ejecutar una sola vez tras init_db.py
"""

import logging
from pathlib import Path
 
import pandas as pd
 
from db.db import bulk_insert
 
logger = logging.getLogger(__name__)

SEED_PATH = Path("data/nutrient.csv")

# Rangos de rank que actúan como agrupadores naturales en el CSV.
# Derivados de observar el CSV, no de documentación oficial — se aplican solo como heurística;
# cualquier nutriente sin match recibe 'other' y puede reclasificarse manualmente después.
RANK_CATEGORY_RULES: list[tuple[float, float, str]] = [
    (50,    2800,  "macro"),      # proximates, energía, carbohidratos, azúcares, fibra, alcoholes de azúcar
    (2850,  5199,  "bioactive"),  # ácidos orgánicos (cítrico, málico, oxálico...)
    (5200,  6249,  "mineral"),    # minerales esenciales
    (6250,  8999,  "vitamin"),    # vitaminas
    (9600,  16230, "lipid"),      # lípidos, ácidos grasos y fitoesteroles
    (16250, 18000, "amino"),      # aminoácidos y compuestos nitrogenados
    (18001, 23200, "bioactive"),  # flavonoides, isoflavonas, polifenoles, cafeína
]


def _assign_category(rank: float) -> str:
    """
    Asigna categoría según el rango de rank del CSV.
    Devuelve 'other' si ningún rango coincide.
    """
    for range_min, range_max, category in RANK_CATEGORY_RULES:
        if range_min <= rank <= range_max:
            return category
    return "other"


def load_nutrients_from_csv() -> None:
    if not SEED_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró {SEED_PATH}.\n"
            "Descárgalo de https://fdc.nal.usda.gov/download-datasets"
        )

    logger.info("Leyendo %s...", SEED_PATH)
    df = pd.read_csv(SEED_PATH, dtype=str)  # todo como string para limpiar antes de convertir

    df = df.rename(columns={"id": "usda_id", "unit_name": "unit"})

    # Limpiar y convertir tipos
    df["usda_id"] = pd.to_numeric(df["usda_id"], errors="coerce")
    df["rank"]    = pd.to_numeric(df["rank"],    errors="coerce")

    # Descartar nutrientes archivados — marcados explícitamente en el nombre
    archived = df["name"].str.contains("DO NOT USE", case=False, na=False)
    logger.info("  Descartados (archivados): %d", archived.sum())
    df = df[~archived]

    df = df.dropna(subset=["usda_id", "nutrient_nbr"])

    # Descartar rank=999999 — la USDA lo usa para nutrientes sin clasificar
    unranked = (df["rank"] == 999999).sum()
    logger.info("  Sin rank asignado (999999): %d", unranked)

    # Asignar categoría desde los rangos de rank
    df["category"] = df["rank"].apply(
        lambda r: _assign_category(r) if pd.notna(r) else "other"
    )

    logger.info("  Total nutrientes a cargar: %d", len(df))
    for category, count in df.groupby("category")["usda_id"].count().items():
        logger.info("    %-12s %d", category, count)

    rows = list(zip(
        df["usda_id"].astype(int),
        df["category"],
        df["nutrient_nbr"],
    ))

    bulk_insert(
        table="nutrient_catalog",
        columns=["usda_id", "category", "nutrient_nbr"],
        rows=rows,
        conflict="(usda_id) DO NOTHING",
    )

    logger.info("%d nutrientes cargados en nutrient_catalog.", len(rows))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s — %(message)s",
    )
    load_nutrients_from_csv()