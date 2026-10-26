"""
scripts/explore_usda_api.py — Exploration script for the USDA FoodData Central API.
 
Shows what /foods/list returns for a specific food and the full foodNutrients structure.
 
Run with:
    python scripts/explore_usda_api.py
"""

import json
import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import USDA_API_KEY, USDA_BASE_URL
 
FOOD_NAME   = "chicken breast"
DATA_TYPE   = "Foundation"
PAGE_SIZE   = 3
 
 
def fetch_foods(name: str, data_type: str, page_size: int) -> list[dict]:
    """Fetches foods from /foods/search matching the given name."""
    url = f"{USDA_BASE_URL}/foods/search"
    params = {
        "api_key":  USDA_API_KEY,
        "query":    name,
        "dataType": data_type,
        "pageSize": page_size,
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("foods", [])
 
 
def print_food_summary(food: dict) -> None:
    """Prints top-level fields returned by /foods/search for a single food."""
    print("\n── Food summary ──────────────────────────────────────")
    print(f"  fdcId:       {food.get('fdcId')}")
    print(f"  description: {food.get('description')}")
    print(f"  dataType:    {food.get('dataType')}")
    print(f"  Top-level keys: {list(food.keys())}")
 
 
def print_food_nutrients(food: dict, limit: int = 10) -> None:
    """Prints the structure of the first `limit` foodNutrients entries."""
    nutrients = food.get("foodNutrients", [])
    print(f"\n── foodNutrients structure (first {limit} of {len(nutrients)}) ──")
    for n in nutrients[:limit]:
        print(f"number: {str(n.get('nutrientNumber', '')):<8} "
              f"name: {str(n.get('nutrientName', '')):<40} "
              f"value: {str(n.get('value', '')):<10} "
              f"unitName: {n.get('unitName')}")

    print(f"\n── Raw first nutrient entry ──────────────────────────")
    if nutrients:
        print(json.dumps(nutrients[0], indent=2))
 
 
if __name__ == "__main__":
    print(f"Searching '{FOOD_NAME}' in {DATA_TYPE}...")
    foods = fetch_foods(FOOD_NAME, DATA_TYPE, PAGE_SIZE)
 
    if not foods:
        print("No foods found. Try a different name or data type.")
    else:
        food = foods[0]
        print_food_summary(food)
        print_food_nutrients(food)