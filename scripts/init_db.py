
from pathlib import Path
from db.db import get_db


def init_db():
    """
    Initializes the database by creating necessary tables and setting up initial data.
    """
    schema = Path("db/schema.sql").read_text(encoding="utf-8")
    print("Initializing database...")
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(schema)
        print("Tables initialized successfully.")

if __name__ == "__main__":
    init_db()