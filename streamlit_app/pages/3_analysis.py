"""
streamlit_app/pages/3_analysis.py — Daily nutritional analysis.
"""

import requests
import streamlit as st
import plotly.graph_objects as go
from datetime import date
import os


API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

COLOR_MAP = {
    "deficit": "#F39C12", # yellow
    "ok":      "#2ECC71", # green
    "warning": "#E74C3C", # red
}

STATUS_LABEL = {
    "deficit": "Possible insufficient intake (below the RDA)",
    "ok":      "Adequate intake",
    "warning": "Possible risk of excess intake (above the UL)",
}


def get_analysis(user_id: int, log_date: date) -> dict | None:
    try:
        response = requests.get(f"{API_URL}/analysis/{user_id}/{log_date}", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def build_chart(nutrients: list[dict]) -> go.Figure | None:
    """Horizontal bar chart showing % of RDA coverage, sorted by percentage descending."""
    with_dri = sorted(
        [n for n in nutrients if n["dri_value"] is not None],
        key=lambda n: n["percentage"],
        reverse=False,  # plotly horizontal bars render bottom-up, so reverse=False = highest on top
    )

    if not with_dri:
        return None

    names       = [n["name"] for n in with_dri]
    percentages = [min(n["percentage"], 200) for n in with_dri]  # cap at 200% for readability
    colors      = [COLOR_MAP.get(n["status"], "#95A5A6") for n in with_dri]
    labels      = [f"{n['percentage']}%" for n in with_dri]

    fig = go.Figure(go.Bar(
        x=percentages,
        y=names,
        orientation="h",
        marker_color=colors,
        text=labels,
        textposition="outside",
    ))

    fig.add_vline(x=100, line_dash="dash", line_color="#2EACCC",
                  annotation_text="100% RDA", annotation_position="top")

    fig.update_layout(
        title="Daily nutrient coverage (% of RDA)",
        xaxis_title="% of RDA",
        yaxis_title="",
        xaxis=dict(range=[0, 220]),
        height=max(400, len(with_dri) * 35),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(color="#2C3E50"),
        margin=dict(l=200),
    )
    return fig


# UI

st.title("📊 Analysis")
st.subheader("My daily nutrition dashboard")

if not st.session_state.get("user_id"):
    st.warning("No active session. Please go to the home page to sign in or create an account.")
    st.stop()

user_id  = st.session_state.user_id

# Date input
log_date = st.date_input("Date", value=date.today(), max_value=date.today())

analysis = get_analysis(user_id, log_date)

if not analysis:
    st.error("Could not retrieve analysis. Make sure the API is running.")
    st.stop()

nutrients = analysis.get("nutrients", [])

if not nutrients:
    st.info("No food entries for this day. Please go to **Food log** to add foods.")
    st.stop()

# Energy summary
caloric_summary = analysis.get("caloric_summary")

if caloric_summary:
    st.subheader("Energy")

    eer               = caloric_summary["eer"]
    caloric_target    = caloric_summary["caloric_target"]
    calories_consumed = caloric_summary["calories_consumed"]
    caloric_balance   = caloric_summary["caloric_balance"]
    goal              = caloric_summary["goal"]
    condition_note    = caloric_summary.get("condition_note")

    col1, col2, col3 = st.columns(3)
    col1.metric("EER", f"{eer} kcal", help="Estimated Energy Requirement — energy needed to maintain your current weight (NASEM DRI 2005)")
    col2.metric("Daily target", f"{caloric_target} kcal", help=f"Adjusted for goal: {goal.replace('_', ' ')}")
    col3.metric("Consumed", f"{calories_consumed} kcal")
 
    if goal == "weight_loss":
        if calories_consumed <= caloric_target:
            st.success(
                f"You are within your caloric target for **{goal.replace('_', ' ')}**. "
                f"Balance: {caloric_balance:+.0f} kcal"
            )
        else:
            st.error(
                f"You exceeded your caloric target for **{goal.replace('_', ' ')}**. "
                f"Balance: {caloric_balance:+.0f} kcal"
            )

    elif goal == "weight_gain":
        if calories_consumed >= caloric_target:
            st.success(
                f"You are meeting your caloric target for **{goal.replace('_', ' ')}**. "
                f"Balance: {caloric_balance:+.0f} kcal"
            )
        else:
            st.warning(
                f"You are below your caloric target for **{goal.replace('_', ' ')}**. "
                f"Balance: {caloric_balance:+.0f} kcal"
            )

    else:  # maintenance
        if abs(caloric_balance) <= 200:
            st.success(
                f"Your intake is close to your maintenance target. "
                f"Balance: {caloric_balance:+.0f} kcal"
            )
        else:
            st.warning(
                f"Your intake differs from your maintenance target. "
                f"Balance: {caloric_balance:+.0f} kcal"
            )

    if condition_note:
        st.caption(f"ℹ️ {condition_note}")

else:
    st.info("Energy analysis unavailable. Make sure your profile includes age, weight, height and activity level.")

st.caption("⚠️ Energy results are population-based estimates, not medical advice. Actual needs depend on your health, activity, and metabolism.")

st.divider()

# Summary metrics
with_dri      = [n for n in nutrients if n["dri_value"] is not None]
deficit_count = sum(1 for n in with_dri if n["status"] == "deficit")
ok_count      = sum(1 for n in with_dri if n["status"] == "ok")
warning_count = sum(1 for n in with_dri if n["status"] == "warning")

st.subheader("Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Deficit",  deficit_count, help=STATUS_LABEL["deficit"])
col2.metric("OK",       ok_count,      help=STATUS_LABEL["ok"])
col3.metric("Warning",  warning_count, help=STATUS_LABEL["warning"])

st.divider()

# Chart
fig = build_chart(nutrients)
if fig:
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No nutrients with DRI recommendations found for this day.")

st.divider()

# Detail table
st.header("Nutrient detail")

sorted_nutrients = sorted(with_dri, key=lambda n: n["percentage"], reverse=True)

col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])
col1.markdown("**Nutrient**")
col2.markdown("**Consumed**")
col3.markdown("**RDA**", help="Recommended Dietary Allowance — the average daily intake level sufficient to meet the nutrient requirements of nearly all (97–98%) healthy individuals. Source: NIH/NCBI — NASEM DRI.")
col4.markdown("**UL**", help="Tolerable Upper Intake Level — the maximum daily intake unlikely to cause adverse health effects. 'ND' means no UL has been established; excess from food alone is unlikely to be harmful. Source: NIH/NCBI — NASEM DRI.")
col5.markdown("**Coverage**")

for n in sorted_nutrients:
    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])
    col1.write(n["name"])
    col2.write(f"{n['consumed']} {n['unit']}")
    col3.write(f"{n['dri_value']} {n['unit']}")
    col4.write(f"{n['ul_value']} {n['unit']}" if n["ul_value"] is not None else "ND")
    coverage_text = f"{n['percentage']}%"
    if n["status"] == "warning":
        col5.markdown(f"<span style='color:#E74C3C'>{coverage_text}</span>", unsafe_allow_html=True)
    else:
        col5.write(coverage_text)

st.divider()

# Disclaimer
st.caption(
    "⚠️ This analysis is for informational purposes only and does not constitute medical advice. Consult a healthcare professional for personalized dietary guidance."
    )