"""
db/db.py — Conexión a PostgreSQL y helpers de acceso a datos.
"""
 
import psycopg2
from psycopg2 import sql as psql
from psycopg2.extras import execute_values, RealDictCursor
from contextlib import contextmanager

from config.config import DB_CONFIG


@contextmanager
def get_db():
    """Abre conexión, hace commit/rollback automático y la cierra."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql: str, params=None) -> list[dict]:
    """Ejecuta una SELECT y devuelve lista de dicts (columna → valor)."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


def fetch_one(sql: str, params=None) -> dict | None:
    """Ejecuta una SELECT y devuelve el primer resultado, o None si no hay."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def execute_sql(sql: str, params=None) -> None:
    """Ejecuta un INSERT / UPDATE / DELETE sin retorno."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def bulk_insert(
    table:    str,
    columns:  list[str],
    rows:     list,
    conflict: str = "DO NOTHING",
) -> None:
    """
    Inserta múltiples filas en una sola llamada a la BD.
 
    Args:
        table:    nombre de la tabla destino.
        columns:  lista de columnas a insertar.
        rows:     lista de tuplas con los valores, en el mismo orden que columns.
        conflict: cláusula ON CONFLICT. Dos formatos válidos:
                  - "DO NOTHING"              → ON CONFLICT DO NOTHING
                  - "(col1, col2) DO NOTHING" → ON CONFLICT (col1, col2) DO NOTHING
    """
    if not rows:
        return
 
    # Construir la cláusula ON CONFLICT
    if conflict.strip().upper() == "DO NOTHING":
        conflict_sql = psql.SQL("DO NOTHING")
    else:
        # Extraer nombres de columnas entre paréntesis: "(col1, col2) DO NOTHING"
        inner = conflict.strip().lstrip("(").split(")")[0]
        conflict_columns = [col.strip() for col in inner.split(",")]
        conflict_sql = psql.SQL("({}) DO NOTHING").format(
            psql.SQL(", ").join(psql.Identifier(col) for col in conflict_columns)
        )
 
    query = psql.SQL("INSERT INTO {} ({}) VALUES %s ON CONFLICT {}").format(
        psql.Identifier(table),
        psql.SQL(", ").join(psql.Identifier(col) for col in columns),
        conflict_sql,
    )
 
    with get_db() as conn:
        with conn.cursor() as cur:
            execute_values(cur, query, rows)