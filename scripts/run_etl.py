import logging
from etl.pipeline import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
)

if __name__ == "__main__":
    run()  # max_pages=None para producción, 2-3 para pruebas rápidas