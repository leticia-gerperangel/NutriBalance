# Schema Design Decisions

## Overview

NutriBalance uses a relational schema designed for transactional operations: recording daily food intake, managing user profiles and retrieving nutritional analysis per user per day.

---

## Table decisions

### `nutrient_catalog` — auxiliary ETL table

This table is not part of the domain model and does not appear in the ERD. The USDA API returns a nutrient number (`nutrient_nbr`) instead of the internal USDA ID. I needed a way to map one to the other during the ETL, so I created `nutrient_catalog` from the USDA `nutrient.csv` file. Without it, the ETL cannot correctly link nutrient data from the API to the `nutrient` table.

It is loaded before the ETL runs and is not used by the application at runtime.

### `recommendation.nutrient_id` references `nutrient.usda_id`

I chose to reference `nutrient.usda_id` directly instead of the internal `nutrient.id`. This made loading the recommendation seed simpler — I already knew the USDA IDs from the source tables, so I did not need an extra query to find the internal IDs first.

### `food.category` and `food.serving_g` are nullable

These fields come from USDA CSV files, not from the API. Not every food has a matching entry in those files, so I made them nullable to avoid discarding valid foods during the ETL.

### `daily_log` UNIQUE constraint on `(user_id, log_date, food_id)`

A user should not be able to log the same food twice on the same day. I added this constraint at the database level to prevent duplicates regardless of what the application does.

### `recommendation` includes `condition`

Nutritional requirements change during pregnancy and lactation. I added `condition` as a column in `recommendation` so the system can apply the correct values for female users in those states, based on the NASEM DRI tables.

### `food_nutrient` carries data, not just a relationship

`food_nutrient` is not just a join table — it stores the `amount` field (nutrient content per 100g of food). This is the core data used in the nutritional analysis.

---

## Index

```sql
CREATE INDEX idx_daily_log_user_date ON daily_log (user_id, log_date);
```

The analysis endpoint always filters `daily_log` by `user_id` and `log_date`. I added this index to avoid full table scans as the table grows with daily entries.

---

## Schema evolution

The schema changed several times as I learned more about the domain:

| Addition | Reason |
|---|---|
| `user_profile.condition` | Nutritional requirements differ during pregnancy and lactation |
| `user_profile.activity_level` | Needed for the EER (energy requirement) calculation |
| `recommendation.ul_value` | To tell apart exceeding the RDA (not harmful) from exceeding the UL (possible risk) |
| `recommendation.condition` | To apply the correct DRI values for pregnancy and lactation |
| `user_profile.username` | Replaced `name` to use as a unique identifier for login |