"""Past sessions, straight out of the local database."""

import io

import pandas as pd
import streamlit as st

import storage
from ui import pick_one, setup_page

setup_page("History", "Everything logged on this device")
storage.init_db()

RANGES = {"7 days": 7, "30 days": 30, "90 days": 90, "All": 3650}

window = pick_one("Range", list(RANGES), key="history_range", default="30 days")
sessions = storage.recent_sessions(days=RANGES[window], limit=5000)

summary = storage.stats()
logs, trained, streak = st.columns(3)
logs.metric("Logs", len(sessions))
trained.metric("Days trained", len({row["timestamp"][:10] for row in sessions}))
streak.metric("Day streak", storage.streak_days())

if not sessions:
    st.info("Nothing logged in this range yet.")
else:
    frame = pd.DataFrame(sessions)
    frame["date"] = frame["timestamp"].str[:10]

    st.subheader("Exercises per day")
    per_day = frame.groupby("date").size().rename("Exercises")
    st.bar_chart(per_day, height=240, color="#F5A524")

    st.subheader("By exercise")
    by_exercise = (
        frame.groupby("exercise")
        .agg(Times=("exercise", "size"), Last=("weight", "last"))
        .sort_values("Times", ascending=False)
        .rename_axis("Exercise")
    )
    st.dataframe(by_exercise, use_container_width=True)

    st.subheader("Log")
    log = frame[["timestamp", "day", "exercise", "sets", "reps", "weight"]].rename(
        columns={
            "timestamp": "When", "day": "Day", "exercise": "Exercise",
            "sets": "Sets", "reps": "Reps", "weight": "Weight",
        }
    )
    st.dataframe(log, use_container_width=True, hide_index=True)

st.markdown("---")
st.subheader("Backup")

buffer = io.StringIO()
pd.DataFrame(storage.all_sessions()).to_csv(buffer, index=False)
st.download_button(
    "Download all sessions (CSV)",
    data=buffer.getvalue(),
    file_name="babod-sessions.csv",
    mime="text/csv",
)

st.caption(
    f"{summary['logs']} logs across {summary['days']} days · "
    f"stored locally at `{summary['db_path']}` ({summary['db_size_kb']} KB)"
)
