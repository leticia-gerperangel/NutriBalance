"""
streamlit_app/pages/1_profile.py — User profile management.
"""

import requests
import streamlit as st
import os


API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def get_user(user_id: int) -> dict | None:
    try:
        response = requests.get(f"{API_URL}/users/{user_id}", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def update_user(user_id: int, data: dict) -> tuple[bool, str]:
    try:
        response = requests.put(f"{API_URL}/users/{user_id}", json=data, timeout=5)
        if response.status_code == 200:
            return True, "Profile updated successfully."
        return False, response.json().get("detail", "Error updating profile.")
    except requests.RequestException:
        return False, "Could not connect to the API."


def delete_user(user_id: int) -> tuple[bool, str]:
    try:
        response = requests.delete(f"{API_URL}/users/{user_id}", timeout=5)
        if response.status_code == 204:
            return True, "Account deleted successfully."
        return False, response.json().get("detail", "Error deleting account.")
    except requests.RequestException:
        return False, "Could not connect to the API."


# UI

st.title("👤 My profile")

# Proteccion de acceso
if not st.session_state.get("user_id"):
    st.warning("No active session. Please sign in or create an account.")
    st.stop()

user = get_user(st.session_state.user_id)

if not user:
    st.error("Could not load user profile.")
    st.stop()

st.header(f"{user['username']}")

# Edit profile
with st.form("form_edit_profile"):
    col1, col2, col3 = st.columns(3)
    with col1:
        age    = st.number_input("Age", value=user["age"], min_value=19, max_value=120)
        weight = st.number_input("Weight (kg)",value=float(user["weight"] or 0), min_value=0.0)
        goal   = st.selectbox("Goal", options=["maintenance", "weight_loss", "weight_gain"],
                                                index=["maintenance", "weight_loss", "weight_gain"].index(user["goal"]))
        
    with col2:
        sex = st.selectbox("Sex", options=["male", "female", "other"], index=["male", "female", "other"].index(user["sex"]))
        height = st.number_input("Height (cm)",  value=float(user["height"] or 0), min_value=0.0)
        activity = st.selectbox("Activity level", options=["sedentary", "low_active", "active", "very_active"],
                                                  index=["sedentary", "low_active", "active", "very_active"].index(user["activity_level"]))
    with col3:
        # Condition only relevant for female
        condition = "none"
        if sex == "female": 
            condition_options = ["none", "pregnancy", "lactation"]
            condition = st.selectbox("Condition", options=condition_options,index=condition_options.index(user["condition"]))       

    submitted = st.form_submit_button("Save changes", type="primary")
    if submitted:
        ok, msg = update_user(st.session_state.user_id, {
            "username": user["username"],
            "age": age, "sex": sex,
            "weight": weight, "height": height,
            "goal": goal, "condition": condition,
            "activity_level": activity
        })
        if ok:
            st.success(msg)
        else:
            st.error(msg)

st.subheader("Delete account")

@st.dialog("Delete account")
def confirm_delete():
    st.warning("⚠️ This action is permanent and cannot be undone. All your food logs will be deleted.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Delete", type="primary", use_container_width=True):
            ok, msg = delete_user(st.session_state.user_id)
            if ok:
                st.session_state.user_id  = None
                st.session_state.username = None
                st.rerun()
            else:
                st.error(msg)

if st.button("Delete account"):
    confirm_delete()