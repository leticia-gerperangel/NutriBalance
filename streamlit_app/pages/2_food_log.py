"""
streamlit_app/pages/2_food_log.py — Daily food intake log.
"""

import requests
import streamlit as st
from datetime import date
import os


API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def search_foods(query: str) -> list[dict]:
    try:
        response = requests.get(f"{API_URL}/foods", params={"search": query}, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


def create_log(user_id: int, fdc_id: int, log_date: date, quantity: float) -> tuple[bool, str]:
    try:
        response = requests.post(
            f"{API_URL}/users/{user_id}/logs",
            json={"fdc_id": fdc_id, "log_date": str(log_date), "quantity": quantity},
            timeout=5,
        )
        if response.status_code == 201:
            return True, "Food logged successfully."
        if response.status_code == 422:
            return False, "Log date cannot be in the future."
        return False, response.json().get("detail", "Error logging food.")
    except requests.RequestException:
        return False, "Could not connect to the API."


def get_logs(user_id: int, log_date: date) -> list[dict]:
    try:
        response = requests.get(f"{API_URL}/users/{user_id}/logs/{log_date}", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


def delete_log(log_id: int) -> tuple[bool, str]:
    try:
        response = requests.delete(f"{API_URL}/logs/{log_id}", timeout=5)
        if response.status_code == 204:
            return True, "Entry removed."
        return False, response.json().get("detail", "Error removing entry.")
    except requests.RequestException:
        return False, "Could not connect to the API."


# UI

st.title("🍽️ My food log")

if not st.session_state.get("user_id"):
    st.warning("No active session. Go to the home page to sign in or create an account.")
    st.stop()

user_id  = st.session_state.user_id
log_date = st.date_input("Date", value=date.today(), max_value=date.today())
st.divider()

# Search and add food

st.subheader("Add food")

search_query = st.text_input("Search food", placeholder="Type at least 2 characters...")

if search_query and len(search_query.strip()) >= 2:
    foods = search_foods(search_query)

    if not foods:
        st.info("No foods found.")
    else:
        food_options       = {f["name"]: f["fdc_id"] for f in foods}
        selected_food_name = st.selectbox("Select your food", options=list(food_options.keys()))
        selected_fdc_id    = food_options[selected_food_name]

        quantity = st.number_input("Quantity (grams)", min_value=1.0, value=100.0, step=10.0)

        if st.button("➕ Add to log", type="primary"):
            ok, msg = create_log(user_id, selected_fdc_id, log_date, quantity)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

st.divider()

# Today's log

st.subheader(f"Log for {log_date.strftime('%B %d, %Y')}")

logs = get_logs(user_id, log_date)

if not logs:
    st.info("No entries for this day.")
else:
    for log in logs:
        col1, col2, col3 = st.columns([4, 2, 1])
        food_name = f" {log['food_name']} 🔸" if not log.get("has_energy") else log["food_name"]
        col1.write(food_name)
        col2.write(f"{log['quantity']} g")
        with col3:
            if st.button("🗑️", key=f"del_{log['id']}"):
                ok, msg = delete_log(log["id"])
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
    if any(not log.get("has_energy") for log in logs):
        st.caption("🔸These foods have no energy data in the USDA database.")