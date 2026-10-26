from dotenv import load_dotenv
import os

load_dotenv()

# Base de datos
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "nutribalance"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

# USDA API 
USDA_API_KEY  = os.getenv("USDA_API_KEY", "DEMO_KEY")
USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# App
APP_ENV       = os.getenv("APP_ENV", "development")  # production en deploy
API_BASE_URL  = os.getenv("API_BASE_URL", "http://localhost:8000")