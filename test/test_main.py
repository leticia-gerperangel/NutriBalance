"""
test/test_main.py — Unit tests for api_backend/main.py business logic.

Run with:
    python -m pytest test/test_main.py -v
"""

import pytest
from api_backend.main import calculate_caloric_summary, calculate_status, calculate_eer

# Calculate status

class TestCalculateStatus:

    def test_below_rda_returns_deficit(self):
        assert calculate_status(consumed=50, dri_value=100, ul_value=None) == "deficit"

    def test_exactly_at_rda_returns_ok(self):
        assert calculate_status(consumed=100, dri_value=100, ul_value=None) == "ok"

    def test_above_rda_below_ul_returns_ok(self):
        assert calculate_status(consumed=150, dri_value=100, ul_value=200) == "ok"

    def test_exactly_at_ul_returns_warning(self):
        assert calculate_status(consumed=200, dri_value=100, ul_value=200) == "warning"

    def test_above_ul_returns_warning(self):
        assert calculate_status(consumed=250, dri_value=100, ul_value=200) == "warning"

    def test_above_rda_no_ul_returns_ok(self):
        # Nutrients with no UL (e.g. Vitamin B-12) — excess from food is not harmful
        assert calculate_status(consumed=500, dri_value=2.4, ul_value=None) == "ok"

    def test_zero_consumed_returns_deficit(self):
        assert calculate_status(consumed=0, dri_value=100, ul_value=None) == "deficit"


# Calculate EER

class TestCalculateEer:

    BASE_MALE = {
        "age": 30, "weight": 80, "height": 177,
        "sex": "male", "activity_level": "sedentary",
    }

    BASE_FEMALE = {
        "age": 30, "weight": 65, "height": 165,
        "sex": "female", "activity_level": "sedentary",
    }

    def test_male_sedentary_returns_float(self):
        result = calculate_eer(self.BASE_MALE)
        assert isinstance(result, float)
        assert result > 0

    def test_female_sedentary_returns_float(self):
        result = calculate_eer(self.BASE_FEMALE)
        assert isinstance(result, float)
        assert result > 0

    def test_male_higher_eer_than_female_same_profile(self):
        # Males generally have higher EER due to different formula coefficients
        male   = {**self.BASE_MALE,   "age": 30, "weight": 70, "height": 170}
        female = {**self.BASE_FEMALE, "age": 30, "weight": 70, "height": 170}
        assert calculate_eer(male) > calculate_eer(female)

    def test_higher_activity_increases_eer(self):
        sedentary   = {**self.BASE_MALE, "activity_level": "sedentary"}
        very_active = {**self.BASE_MALE, "activity_level": "very_active"}
        assert calculate_eer(very_active) > calculate_eer(sedentary)

    def test_missing_weight_returns_none(self):
        user = {**self.BASE_MALE, "weight": None}
        assert calculate_eer(user) is None

    def test_missing_height_returns_none(self):
        user = {**self.BASE_MALE, "height": None}
        assert calculate_eer(user) is None

    def test_missing_age_returns_none(self):
        user = {**self.BASE_MALE, "age": None}
        assert calculate_eer(user) is None

    def test_sex_other_returns_none(self):
        # Formula only defined for male and female
        user = {**self.BASE_MALE, "sex": "other"}
        assert calculate_eer(user) is None

    def test_older_age_decreases_eer(self):
        young = {**self.BASE_MALE, "age": 25}
        old   = {**self.BASE_MALE, "age": 65}
        assert calculate_eer(young) > calculate_eer(old)


class TestCalculateCaloricSummary:

    def test_uses_calories_from_logged_foods(self):
        summary = calculate_caloric_summary(
            calories_consumed=750.0,
            user={"goal": "maintenance"},
            eer=2000.0,
        )

        assert summary["calories_consumed"] == 750.0
        assert summary["caloric_balance"] == -1250.0