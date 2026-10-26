"""
streamlit_app/app.py — Punto de entrada de NutriBalance Dashboard.

Ejecutar con:
    streamlit run streamlit_app/app.py
"""

import requests
import streamlit as st
import os


API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="NutriBalance",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos globales
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF; }
        h1, h2, h3 { color: #2C3E50; }
    </style>
""", unsafe_allow_html=True)

# Estado de sesión
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("username", None)


# Helpers

def login(username: str) -> bool:
    """Busca el usuario por username y lo carga en session_state. Devuelve True si existe."""
    try:
        response = requests.get(f"{API_URL}/users/username/{username.strip()}", timeout=5)
        if response.status_code == 200:
            user = response.json()
            st.session_state.user_id  = user["id"]
            st.session_state.username = user["username"]
            return True
        return False
    except requests.RequestException:
        st.error("Could not connect to API. Make sure it's running on localhost:8000.")
        return False
 

def register(data: dict) -> tuple[bool, str]:
    """Crea un nuevo usuario. Devuelve (éxito, mensaje)."""
    try:
        response = requests.post(f"{API_URL}/users", json=data, timeout=5)
        if response.status_code == 201:
            user = response.json()
            st.session_state.user_id  = user["id"]
            st.session_state.username = user["username"]
            return True, "Account created successfully."
        return False, response.json().get("detail", "Error creating account.")
    except requests.RequestException:
        return False, "Could not connect to API."


def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.rerun()


# Home sin sesión iniciada

def show_login_register():
    st.title("🥗 NutriBalance")
    st.header("Daily nutritional analysis dashboard")

    tab_login, tab_register = st.tabs(["Sign in", "Create account"])

    # Sign in
    with tab_login:
        username_input = st.text_input("Username", placeholder="Write your username...")
        if st.button("Sign in", type="primary"):
            if not username_input.strip():
                st.error("Please enter a username.")
            else:
                if login(username_input):
                    st.rerun()
                else:
                    st.warning(f"The user '{username_input}' does not exist. Please go to the **Create account** tab.")

    # Create account
    with tab_register:
        with st.form("form_registro"):
            col1, col2 = st.columns(2)
            with col1:
                username  = st.text_input("Username", max_chars=50)
                age       = st.number_input("Age", min_value=19, max_value=120, value=30)
                sex       = st.selectbox("Sex", options=["male", "female", "other"])
                condition = st.selectbox("Condition", options=["none", "pregnancy", "lactation"])
            with col2:
                weight    = st.number_input("Weight (kg)", min_value=0.0, value=70.0)
                height    = st.number_input("Height (cm)", min_value=0.0, value=170.0)
                goal      = st.selectbox("Goal", options=["maintenance", "weight_loss", "weight_gain"])
                activity_level = st.selectbox("Activity level", options=["sedentary", "low_active", "active", "very_active"])
                

            submitted = st.form_submit_button("Create account", type="primary")
            if submitted:
                if not username.strip():
                    st.error("The username cannot be empty.")
                elif condition in ("pregnancy", "lactation") and sex != "female":
                    st.error("The conditions 'pregnancy' and 'lactation' are only valid for female sex.")
                else:
                    ok, msg = register({
                        "username": username.strip(),
                        "age": age, "sex": sex,
                        "weight": weight, "height": height,
                        "goal": goal, "condition": condition,
                        "activity_level": activity_level
                    })
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


# Home con sesión iniciada

def show_home():
    st.title(f"👋 Welcome, {st.session_state.username}")
    st.divider()

    st.subheader("Good nutrition starts with understanding your day.")

    st.write("See how your food intake compares with your daily nutrient recommendations, spot nutrients that may need attention, and make more informed choices over time.")

    st.caption("Recommendations are based on Dietary Reference Intakes (DRIs) from the National Academies of Sciences, Engineering, and Medicine.")

    st.divider()

    st.subheader("Your next steps")

    col1, col2, col3 = st.columns(3)
    col1.info("**1. Complete your profile**\n\nPersonalize your nutrient references.")
    col2.info("**2. Log your food**\n\nRecord what you eat and drink today.")
    col3.info("**3. Review your analysis**\n\nSee your nutrient intake at a glance.")


# Main
if st.session_state.username:
    pages = {
        "": [
            st.Page(
                show_home,
                title="Home",
                icon="🏠",
                default=True,
            ),
        ],
        "Your account": [
            st.Page(
                "pages/1_profile.py",
                title="Profile",
                icon="👤",
            ),
            st.Page(
                logout,
                title="Sign out",
                icon=":material/logout:",
            ),
        ],
        "Reports": [
            st.Page(
                "pages/2_food_log.py",
                title="Food log",
                icon="🍽️",
            ),
            st.Page(
                "pages/3_analysis.py",
                title="Analysis",
                icon="📊",
            ),
        ],
    }

    pg = st.navigation(pages, position="sidebar", expanded=True)
    pg.run()

else:
    pg = st.navigation(
        [st.Page(show_login_register, title="Sign in", default=True)],
        position="hidden"
    )
    pg.run()