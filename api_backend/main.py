"""
api_backend/main.py — API REST de NutriBalance.

Endpoints:
    GET  /foods                      Buscar alimentos por nombre
    GET  /foods/{fdc_id}/nutrients   Detalle nutricional de un alimento
    POST /users                      Crear perfil de usuario
    GET  /users/username/{username}  Obtener perfil de usuario por username
    GET  /users/{user_id}            Obtener perfil de usuario
    PUT  /users/{user_id}            Actualizar perfil de usuario
    DELETE /users/{user_id}          Eliminar perfil de usuario
    POST /logs                       Registrar ingesta diaria
    GET  /logs/{user_id}/{date}      Obtener ingesta de un día
    DELETE /logs/{log_id}            Eliminar un registro de ingesta
    GET  /analysis/{user_id}/{date}  Análisis nutricional del día
"""

from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from db.db import fetch_all, fetch_one, execute_sql

app = FastAPI(title="NutriBalance API", version="1.0.0")

# Umbrales de análisis nutricional (% del RDA)
# Fuente: simplificación para portfolio — ver README para justificación
DEFICIT_THRESHOLD = 80.0   # < 80%  → déficit
OK_THRESHOLD      = 100.0  # 80-100% → ok, > 100% → exceso


# Schemas

class UserCreate(BaseModel):
    username:      str      = Field(..., min_length=1, max_length=50)
    age:       int          = Field(..., ge=19, le=120)
    sex:       str          = Field(..., pattern="^(male|female|other)$")
    weight: Optional[float] = Field(None, ge=0, description="Weight in kg")
    height: Optional[float] = Field(None, ge=0, description="Height in cm")
    goal:      str          = Field("maintenance", pattern="^(weight_loss|weight_gain|maintenance)$")
    condition: str          = Field("none", pattern="^(none|pregnancy|lactation)$")
    activity_level: str     = Field("sedentary", pattern="^(sedentary|low_active|active|very_active)$")


class LogCreate(BaseModel):
    fdc_id:   int
    log_date: date  = Field(..., description="Date of registration in YYYY-MM-DD format")
    quantity: float = Field(..., gt=0, description="Consumed amount in grams")

    @field_validator("log_date")
    @classmethod
    def log_date_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Log date cannot be in the future.")
        return v


# Alimentos

@app.get("/foods")
def search_foods(search: str, limit: int = 20):
    """Busca alimentos por nombre. Mínimo 2 caracteres."""
    if len(search.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search term must be at least 2 characters long.")

    rows = fetch_all(
        "SELECT fdc_id, name, category, serving_g FROM food WHERE name ILIKE %s LIMIT %s",
        (f"%{search}%", limit),
    )
    return rows


@app.get("/foods/{fdc_id}/nutrients")
def get_food_nutrients(fdc_id: int):
    """Devuelve el detalle nutricional de un alimento por fdc_id."""
    food = fetch_one(
        "SELECT fdc_id, name, category, serving_g FROM food WHERE fdc_id = %s",
        (fdc_id,),
    )
    if not food:
        raise HTTPException(status_code=404, detail=f"Food with fdc_id={fdc_id} not found.")

    nutrients = fetch_all(
        """
        SELECT n.usda_id, n.name, n.unit, fn.amount
        FROM food_nutrient fn
        JOIN nutrient n ON fn.nutrient_id = n.id
        WHERE fn.food_id = (SELECT id FROM food WHERE fdc_id = %s)
        ORDER BY n.name
        """,
        (fdc_id,),
    )
    return {**food, "nutrients": nutrients}


# Usuarios

@app.post("/users", status_code=201)
def create_user(user: UserCreate):
    """Crea un nuevo perfil de usuario."""
    # pregnancy y lactation solo son válidos para female
    if user.condition in ("pregnancy", "lactation") and user.sex != "female":
        raise HTTPException(
            status_code=400,
            detail="The conditions 'pregnancy' and 'lactation' are only valid for sex='female'."
        )

    existing = fetch_one("SELECT id FROM user_profile WHERE username = %s", (user.username,))
    if existing:
        raise HTTPException(status_code=409, detail=f"A user with the name '{user.username}' already exists.")

    execute_sql(
        """
        INSERT INTO user_profile (username, age, sex, condition, weight, height, goal, activity_level)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (user.username, user.age, user.sex, user.condition, user.weight, user.height, user.goal, user.activity_level),
    )
    return fetch_one("SELECT * FROM user_profile WHERE username = %s", (user.username,))


@app.get("/users/username/{username}")
def get_user_by_username(username: str):
    """Obtiene un usuario por username."""
    user = fetch_one(
        "SELECT * FROM user_profile WHERE username = %s", (username,)
    )
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")
    return user


@app.get("/users/{user_id}")
def get_user(user_id: int):
    """Obtiene el perfil de un usuario por id."""
    user = fetch_one("SELECT * FROM user_profile WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id={user_id} not found.")
    return user


@app.put("/users/{user_id}", status_code=200)
def update_user(user_id: int, user: UserCreate):
    """Actualiza el perfil de un usuario."""
    existing = fetch_one("SELECT id FROM user_profile WHERE id = %s", (user_id,))
    if not existing:
        raise HTTPException(status_code=404, detail=f"User with id={user_id} not found.")

    if user.condition in ("pregnancy", "lactation") and user.sex != "female":
        raise HTTPException(
            status_code=400,
            detail="The conditions 'pregnancy' and 'lactation' are only valid for sex='female'."
        )

    execute_sql(
        """
        UPDATE user_profile 
        SET username=%s, age=%s, sex=%s, condition=%s, weight=%s, height=%s, goal=%s, activity_level=%s
        WHERE id = %s
        """,
        (user.username, user.age, user.sex, user.condition, user.weight, user.height, user.goal, user.activity_level, user_id),
    )
    return fetch_one("SELECT * FROM user_profile WHERE id = %s", (user_id,))


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    """Elimina un usuario y todos sus logs asociados."""
    user = fetch_one("SELECT id FROM user_profile WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id={user_id} not found.")

    execute_sql("DELETE FROM user_profile WHERE id = %s", (user_id,))


# Log diario

@app.post("/users/{user_id}/logs", status_code=201)
def create_log(user_id: int, log: LogCreate):
    """Registra la ingesta de un alimento para un usuario en una fecha."""
    user = fetch_one("SELECT id FROM user_profile WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id={user_id} not found.")

    food = fetch_one("SELECT id FROM food WHERE fdc_id = %s", (log.fdc_id,))
    if not food:
        raise HTTPException(status_code=404, detail=f"Food with fdc_id={log.fdc_id} not found.")

    existing = fetch_one(
        "SELECT id FROM daily_log WHERE user_id = %s AND food_id = %s AND log_date = %s",
        (user_id, food["id"], log.log_date),
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A record already exists for this food on this date. Delete it before inserting again."
        )

    execute_sql(
        "INSERT INTO daily_log (user_id, food_id, log_date, quantity) VALUES (%s, %s, %s, %s)",
        (user_id, food["id"], log.log_date, log.quantity),
    )
    return fetch_one(
        """
        SELECT dl.id, dl.user_id, dl.log_date, dl.quantity, f.fdc_id, f.name AS food_name
        FROM daily_log dl
        JOIN food f ON dl.food_id = f.id
        WHERE dl.user_id = %s AND dl.food_id = %s AND dl.log_date = %s
        """,
        (user_id, food["id"], log.log_date),
    )


@app.get("/users/{user_id}/logs/{log_date}")
def get_logs(user_id: int, log_date: date):
    """Devuelve todos los registros de ingesta de un usuario para una fecha."""
    user = fetch_one("SELECT id FROM user_profile WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id={user_id} not found.")

    rows = fetch_all(
        """
       SELECT dl.id, dl.log_date, dl.quantity, f.fdc_id, f.name AS food_name, f.serving_g,
       EXISTS (
           SELECT 1 FROM food_nutrient fn
           JOIN nutrient n ON fn.nutrient_id = n.id
           WHERE fn.food_id = f.id AND n.usda_id = 1008 AND fn.amount > 0
       ) AS has_energy
       FROM daily_log dl
       JOIN food f ON dl.food_id = f.id
       WHERE dl.user_id = %s AND dl.log_date = %s
       ORDER BY f.name
        """,
        (user_id, log_date),
    )
    return rows


@app.delete("/logs/{log_id}", status_code=204)
def delete_log(log_id: int):
    """Elimina un registro de ingesta por id."""
    existing = fetch_one("SELECT id FROM daily_log WHERE id = %s", (log_id,))
    if not existing:
        raise HTTPException(status_code=404, detail=f"Record with id={log_id} not found.")

    execute_sql("DELETE FROM daily_log WHERE id = %s", (log_id,))


# Análisis

def calculate_status(consumed: float, dri_value: float, ul_value: float | None) -> str:
    if ul_value is not None and consumed >= ul_value:
        return "warning"
    if consumed >= dri_value:
        return "ok"
    return "deficit"

PA_COEFFICIENTS = {
    "male":   {"sedentary": 1.0, "low_active": 1.11, "active": 1.25, "very_active": 1.48},
    "female": {"sedentary": 1.0, "low_active": 1.12, "active": 1.27, "very_active": 1.45},
}

def calculate_eer(user: dict) -> float | None:
    """
    Calculates Estimated Energy Requirement using NASEM DRI 2005 equations.
    Not applied for pregnancy or lactation — condition_note is added instead.
    Returns None if required user data is missing.
    """
    age      = user.get("age")
    weight   = user.get("weight")
    height   = user.get("height")
    sex      = user.get("sex")
    activity = user.get("activity_level", "sedentary")

    if not all([age, weight, height]) or sex not in PA_COEFFICIENTS:
        return None

    pa       = PA_COEFFICIENTS[sex].get(activity, 1.0)
    weight_f = float(weight)
    height_m = float(height) / 100

    if sex == "male":
        return round(662 - (9.53 * age) + pa * (15.91 * weight_f + 539.6 * height_m), 1)
    else:
        return round(354 - (6.91 * age) + pa * (9.36 * weight_f + 726 * height_m), 1)


def calculate_caloric_summary(user: dict, eer: float | None, calories_consumed: float) -> dict | None:
    """
    Extracts caloric intake from nutrient list and calculates balance vs goal target.
    Returns None if EER cannot be calculated.
    """
    if eer is None:
        return None

    goal = user.get("goal", "maintenance")
    if goal == "weight_loss":
        caloric_target = round(eer - 500, 1)
    elif goal == "weight_gain":
        caloric_target = round(eer + 500, 1)
    else:
        caloric_target = eer

    condition = user.get("condition", "none")
    condition_note = (
        "EER calculated without adjustment for pregnancy or lactation. "
        "Actual energy needs may be higher."
        if condition in ("pregnancy", "lactation") else None
    )

    return {
        "eer":               eer,
        "caloric_target":    caloric_target,
        "calories_consumed": calories_consumed,
        "caloric_balance":   round(calories_consumed - caloric_target, 1),
        "goal":              goal,
        "condition_note":    condition_note,
    }


def build_nutrient_analysis(intake_rows: list, dri_map: dict) -> list:
    """
    Crosses nutrient intake with recommendations and calculates status and percentage.
    """
    nutrients = []
    for row in intake_rows:
        consumed = round(float(row["consumed"]), 2)
        dri_data = dri_map.get(row["usda_id"])

        if dri_data is not None:
            dri_value, ul_value = dri_data
            percentage = round(consumed / float(dri_value) * 100, 1)
            status     = calculate_status(consumed, float(dri_value), ul_value)
        else:
            dri_value  = None
            ul_value   = None
            percentage = None
            status     = None

        nutrients.append({
            "usda_id":    row["usda_id"],
            "name":       row["name"],
            "unit":       row["unit"],
            "consumed":   consumed,
            "dri_value":  dri_value,
            "ul_value":   ul_value,
            "percentage": percentage,
            "status":     status,
        })

    return nutrients

@app.get("/analysis/{user_id}/{log_date}")
def get_daily_analysis(user_id: int, log_date: date):
    user = fetch_one("SELECT * FROM user_profile WHERE id = %s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id={user_id} not found.")

    intake_rows = fetch_all(
        """
        SELECT n.usda_id, n.name, n.unit,
               SUM(fn.amount * dl.quantity / 100.0) AS consumed
        FROM daily_log dl
        JOIN food f        ON dl.food_id     = f.id
        JOIN food_nutrient fn ON f.id        = fn.food_id
        JOIN nutrient n    ON fn.nutrient_id = n.id
        WHERE dl.user_id = %s AND dl.log_date = %s
        GROUP BY n.usda_id, n.name, n.unit
        ORDER BY n.name
        """,
        (user_id, log_date),
    )

    if not intake_rows:
        return {"user_id": user_id, "log_date": log_date, "nutrients": [], "caloric_summary": None}

    recommendations = fetch_all(
        """
        SELECT nutrient_id, dri_value, ul_value
        FROM recommendation
        WHERE sex = %s AND condition = %s
          AND age_min <= %s AND age_max >= %s
        """,
        (user["sex"], user["condition"], user["age"], user["age"]),
    )
    dri_map = {row["nutrient_id"]: (row["dri_value"], row["ul_value"]) for row in recommendations}

    nutrients        = build_nutrient_analysis(intake_rows, dri_map)
    eer              = calculate_eer(user)

    energy_row = next((r for r in intake_rows if r["usda_id"] == 1008), None)
    calories_consumed = round(float(energy_row["consumed"]), 1) if energy_row else 0.0

    caloric_summary  = calculate_caloric_summary(user, eer, calories_consumed)

    return {
        "user_id":         user_id,
        "log_date":        log_date,
        "nutrients":       nutrients,
        "caloric_summary": caloric_summary,
    }