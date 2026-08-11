"""Workout tracker — mobile-first Streamlit UI backed by local SQLite."""

import os

import streamlit as st

import storage
from ui import format_weight, pick_one, rerun, setup_page


@st.cache_resource
def _database():
    """Create/seed the database once per server process."""
    storage.init_db()
    return storage.db_path()


def suggested_day(days):
    """Pick the day to open on: the one in progress, else the next in rotation."""
    if not days:
        return None

    today = storage.today_str()
    for session in storage.recent_sessions(days=14, limit=200):
        if session["timestamp"].startswith(today) and session["day"] in days:
            return session["day"]

    for session in storage.recent_sessions(days=14, limit=200):
        if session["day"] in days:
            return days[(days.index(session["day"]) + 1) % len(days)]

    return days[0]


def on_weight_change(exercise, widget_key):
    storage.set_exercise_weight(exercise, st.session_state[widget_key])
    st.toast(f"{exercise} → {format_weight(st.session_state[widget_key])}", icon="🏋️")


def exercise_card(workout, completed_at):
    """One tappable exercise. Returns True if the plan changed and we should rerun."""
    name = workout["name"]
    weight_key = f"weight_{workout['id']}"

    with st.container(border=True):
        header, weight = st.columns([3, 2])
        with header:
            st.markdown(f"**{name}**")
            st.caption(f"{workout['sets']} × {workout['reps']}")
        with weight:
            st.markdown(
                f"<div style='text-align:right;font-size:1.35rem;font-weight:700'>"
                f"{format_weight(workout['weight'])}</div>",
                unsafe_allow_html=True,
            )

        if workout["description"]:
            st.caption(workout["description"])

        if completed_at:
            # Compact row once it's logged, so the unfinished work stays in view.
            status, undo = st.columns([3, 2])
            status.markdown(f"✅ **Done** at {completed_at}")
            if undo.button("Undo", key=f"undo_{workout['id']}"):
                storage.unlog_workout(name)
                return True
        else:
            if st.button("Mark complete", key=f"log_{workout['id']}", type="primary"):
                storage.log_workout(
                    exercise=name,
                    sets=workout["sets"],
                    reps=workout["reps"],
                    weight=workout["weight"],
                    description=workout["description"],
                    day=workout["day"],
                )
                return True

            with st.expander("Adjust weight"):
                st.number_input(
                    "Weight (lbs)",
                    min_value=0.0,
                    step=5.0,
                    value=float(workout["weight"]),
                    key=weight_key,
                    on_change=on_weight_change,
                    args=(name, weight_key),
                    help="Saved right away, for every day this exercise appears.",
                )

    return False


def main():
    setup_page("Workout Tracker", storage.now_local().strftime("%A, %B %-d"))
    _database()

    days = storage.list_days()
    if not days:
        st.info(
            "No workout plan yet. Add exercises on the **Plan & Weights** page, "
            "or import an existing Google Sheet with "
            "`python scripts/import_from_sheets.py`."
        )
        return

    if "selected_day" not in st.session_state:
        st.session_state.selected_day = suggested_day(days)

    selected = pick_one(
        "Workout day", days, key="day_picker", default=st.session_state.selected_day
    )
    st.session_state.selected_day = selected

    workouts = storage.get_workouts(selected)
    completed = storage.completed_on()

    done = sum(1 for workout in workouts if workout["name"] in completed)
    if workouts:
        st.progress(done / len(workouts), text=f"{done} of {len(workouts)} done today")

    for workout in workouts:
        if exercise_card(workout, completed.get(workout["name"])):
            rerun()

    if workouts and done == len(workouts):
        st.success(f"{selected} complete. Nice work.")

    st.markdown("---")
    streak = storage.streak_days()
    left, right = st.columns(2)
    left.metric("Logged today", len(completed))
    right.metric("Day streak", streak)

    if hasattr(st, "page_link"):
        st.page_link("pages/1_Plan_and_Weights.py", label="Plan & weights", icon="⚙️")
        st.page_link("pages/2_History.py", label="History", icon="📈")

    # Keep-alive marker rewritten hourly by .github/workflows/keepalive.yml for
    # the Streamlit Cloud deployment; hidden unless BABOD_SHOW_KEEPALIVE=1.
    if os.getenv("BABOD_SHOW_KEEPALIVE") == "1":
        st.text("Today is 2026-08-11-15")


if __name__ == "__main__":
    main()
