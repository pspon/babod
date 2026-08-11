"""Edit the workout plan: weights, sets/reps, and which exercises exist."""

import streamlit as st

import storage
from ui import format_weight, pick_one, rerun, setup_page

setup_page("Plan & Weights", "Progressive overload lives here")
storage.init_db()

days = storage.list_days()

if days:
    selected = pick_one("Workout day", days, key="plan_day")
    workouts = storage.get_workouts(selected)

    st.caption(f"{len(workouts)} exercises in {selected}")

    for workout in workouts:
        name = workout["name"]
        with st.container(border=True):
            header, weight = st.columns([3, 2])
            header.markdown(f"**{name}**")
            header.caption(f"{workout['sets']} × {workout['reps']}")
            weight.markdown(
                f"<div style='text-align:right;font-size:1.35rem;font-weight:700'>"
                f"{format_weight(workout['weight'])}</div>",
                unsafe_allow_html=True,
            )

            with st.expander("Edit"):
                with st.form(f"edit_{workout['id']}"):
                    new_weight = st.number_input(
                        "Weight (lbs)",
                        min_value=0.0,
                        step=5.0,
                        value=float(workout["weight"]),
                        help="0 means bodyweight.",
                    )
                    sets_col, reps_col = st.columns(2)
                    new_sets = sets_col.text_input("Sets", value=str(workout["sets"]))
                    new_reps = reps_col.text_input("Reps", value=str(workout["reps"]))
                    new_description = st.text_input(
                        "Notes", value=workout["description"]
                    )

                    save, delete = st.columns(2)
                    if save.form_submit_button("Save", type="primary"):
                        storage.upsert_exercise(
                            day=selected,
                            name=name,
                            sets=new_sets,
                            reps=new_reps,
                            weight=new_weight,
                            description=new_description,
                            position=workout["position"],
                        )
                        # The working weight is per exercise, not per day.
                        storage.set_exercise_weight(name, new_weight)
                        st.toast(f"Saved {name}", icon="✅")
                        rerun()

                    if delete.form_submit_button("Delete"):
                        storage.delete_exercise(selected, name)
                        st.toast(f"Removed {name} from {selected}", icon="🗑️")
                        rerun()
else:
    selected = None
    st.info("No exercises yet — add your first one below.")

st.markdown("---")

with st.expander("Add an exercise", expanded=not days):
    with st.form("add_exercise", clear_on_submit=True):
        day_options = days + ["➕ New day…"]
        day_choice = st.selectbox(
            "Day", day_options, index=day_options.index(selected) if selected else 0
        )
        new_day_name = st.text_input(
            "New day name", value="", placeholder=f"Day {len(days) + 1}"
        )
        name = st.text_input("Exercise name")
        sets_col, reps_col = st.columns(2)
        sets = sets_col.text_input("Sets", value="3")
        reps = reps_col.text_input("Reps", value="10")
        weight = st.number_input("Weight (lbs)", min_value=0.0, step=5.0, value=0.0)
        description = st.text_input("Notes", value="")

        if st.form_submit_button("Add exercise", type="primary"):
            day = new_day_name.strip() if day_choice == "➕ New day…" else day_choice
            if not day:
                st.error("Give the new day a name.")
            elif not name.strip():
                st.error("Give the exercise a name.")
            else:
                storage.upsert_exercise(
                    day=day,
                    name=name.strip(),
                    sets=sets,
                    reps=reps,
                    weight=weight,
                    description=description,
                )
                st.toast(f"Added {name.strip()} to {day}", icon="➕")
                rerun()
