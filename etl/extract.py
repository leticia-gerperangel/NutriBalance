"""
etl/extract.py — Extracción de alimentos desde la API USDA FoodData Central.
"""

import logging
import time

import requests

from config.config import USDA_API_KEY, USDA_BASE_URL

logger = logging.getLogger(__name__)

USDA_DATA_TYPES = ("Foundation", "SR Legacy")
PAGE_SIZE       = 200  # máximo permitido por la API
MAX_RETRIES     = 3
INTER_PAGE_SLEEP = 0.1


def fetch_all_foods(max_pages: int | None = None) -> list[dict]:
    """
    Endpoint /foods/list para Foundation y SR Legacy.
    Devuelve todos los alimentos únicos (deduplicados por fdcId).

    Args:
        max_pages: límite de páginas por data_type. None = sin límite (producción).
                   Pasa 2 ó 3 para pruebas rápidas.
    """
    all_foods: list[dict] = []
    seen_ids:  set[int]   = set()

    for data_type in USDA_DATA_TYPES:
        logger.info("Paginando '%s'...", data_type)
        page = 1

        while True:
            items = _fetch_page(data_type, page)

            if not items:
                break

            for item in items:
                fdc_id = item.get("fdcId")
                if fdc_id and fdc_id not in seen_ids:
                    seen_ids.add(fdc_id)
                    all_foods.append(item)

            logger.info("  Página %d | total acumulado: %d", page, len(all_foods))

            if max_pages is not None and page >= max_pages:
                break

            page += 1
            time.sleep(INTER_PAGE_SLEEP)

    logger.info("Extracción completada: %d alimentos únicos.", len(all_foods))
    return all_foods


def _fetch_page(data_type: str, page: int) -> list[dict]:
    """
    Llama a /foods/list y devuelve la lista de alimentos de esa página.
    Reintenta hasta MAX_RETRIES veces ante errores de red.

    Raises:
        RuntimeError: si la API no responde tras todos los intentos.
    """
    url = f"{USDA_BASE_URL}/foods/list"
    params = {
        "api_key":    USDA_API_KEY,
        "dataType":   data_type,
        "pageSize":   PAGE_SIZE,
        "pageNumber": page,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                logger.error("API USDA sin respuesta tras %d intentos: %s", MAX_RETRIES, e)
                raise RuntimeError(
                    f"API USDA no respondió tras {MAX_RETRIES} intentos "
                    f"(data_type='{data_type}', página {page})."
                ) from e

            logger.warning("Intento %d/%d fallido (%s). Reintentando...", attempt, MAX_RETRIES, e)
            time.sleep(attempt)  # 1s, 2s, 3s