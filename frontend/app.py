import os
from datetime import date

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def post_plan(payload: dict) -> dict:
    resp = requests.post(f"{BACKEND_URL}/plan", json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_plan(trip_id: str) -> dict:
    resp = requests.get(f"{BACKEND_URL}/plan/{trip_id}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def post_book(trip_id: str) -> dict:
    resp = requests.post(f"{BACKEND_URL}/plan/{trip_id}/book", timeout=15)
    resp.raise_for_status()
    return resp.json()


def comma_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


st.set_page_config(page_title="Vacation Planner", layout="wide")
st.title("Vacation Planner (PoC)")
st.caption("Backend: FastAPI | UI: Streamlit | Bookings simulated")

with st.sidebar.form("preferences_form"):
    st.subheader("Trip preferences")
    destinations = st.text_input(
        "Destinations (comma-separated)", value="Lisbon, Bali"
    )
    min_days = st.number_input("Min duration (days)", min_value=1, max_value=30, value=3)
    max_days = st.number_input("Max duration (days)", min_value=min_days, max_value=30, value=5)
    budget_max = st.number_input("Budget max ($)", min_value=100.0, value=1500.0, step=50.0)
    budget_min = st.number_input("Budget min ($)", min_value=0.0, value=800.0, step=50.0)
    travel_style = st.selectbox(
        "Travel style",
        options=["relaxing", "adventure", "family", "business"],
        index=0,
    )
    start_date = st.date_input("Start date (optional)", value=None)
    end_date = st.date_input("End date (optional)", value=None)
    notes = st.text_area("Notes", placeholder="Visa constraints, flight prefs, etc.", height=80)
    submitted = st.form_submit_button("Generate plan")

if submitted:
    payload: dict = {
        "destination_preferences": comma_list(destinations),
        "min_duration_days": int(min_days),
        "max_duration_days": int(max_days),
        "budget_min": float(budget_min),
        "budget_max": float(budget_max),
        "travel_style": travel_style,
        "notes": notes or None,
    }
    if isinstance(start_date, date):
        payload["start_date"] = start_date.isoformat()
    if isinstance(end_date, date):
        payload["end_date"] = end_date.isoformat()
    try:
        result = post_plan(payload)
        st.session_state["current_plan"] = result["plan"]
        st.success("Plan generated")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to generate plan: {exc}")
        st.session_state.pop("current_plan", None)

plan = st.session_state.get("current_plan")

if plan:
    st.header(f"Trip to {plan['destination']} ({plan['start_date']} → {plan['end_date']})")
    cols = st.columns(3)
    cols[0].metric("Total budget", f"${plan['budget_summary']['total_estimated']:.0f}")
    cols[1].metric("Flight", f"${plan['budget_summary']['breakdown'].get('flight', 0):.0f}")
    cols[2].metric("Hotel", f"${plan['budget_summary']['breakdown'].get('hotel', 0):.0f}")

    for day in plan["days"]:
        with st.expander(f"{day['date']}"):
            for activity in day["activities"]:
                st.markdown(
                    f"**{activity['time_of_day'].title()} — {activity['title']}**  \n"
                    f"{activity['description']}  \n"
                    f"Cost: ${activity['cost_estimate']:.0f} | "
                    f"Booking required: {'Yes' if activity['booking_required'] else 'No'}"
                )

    if st.button("Book this trip (simulate)"):
        try:
            booking_resp = post_book(plan["trip_id"])
            st.session_state["last_booking"] = booking_resp
            st.success("Bookings simulated")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Booking failed: {exc}")

booking = st.session_state.get("last_booking")
if booking:
    st.subheader("Booking summary")
    for record in booking["bookings"]:
        st.markdown(
            f"- **{record['type'].title()}** | {record['provider']} | "
            f"${record['price']:.0f} | status: {record['status']}"
        )
