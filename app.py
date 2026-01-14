import streamlit as st
from streamlit_js_eval import streamlit_js_eval
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import json

# Authenticate with Google Sheets API.
def authenticate_google_sheets():
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credential_json_string = st.secrets["barabod"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credential_json_string, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# Get workout data from the specified template (day).
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_workout_template(template_name):
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet(template_name)
    return worksheet.get_all_records()

# Fetch today’s completed workouts.
@st.cache_data(ttl=60)  # Cache for 1 minute since this changes frequently
def get_completed_workouts_today():
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)
    session_worksheet = sheet.worksheet('Session Data')

    today = datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d')
    records = session_worksheet.get_all_records()
    return {record['exercise'] for record in records if record['timestamp'].startswith(today)}

# Save a completed workout.
def save_workout_session(workout):
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)
    session_worksheet = sheet.worksheet('Session Data')

    timestamp = datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S')
    session_worksheet.append_row([
        timestamp,
        workout['exercise'],
        workout['sets'],
        workout['reps'],
        workout['weight'],
        True,
        workout['description']
    ])



# Main Streamlit app.
def main():
    st.title("Workout Tracker")

    # Detect the browser window's width.
    width = streamlit_js_eval(js_expressions="window.innerWidth", key="device_width")
    #st.write("Detected window width:", width)
    try:
        width_val = int(width)
    except Exception as e:
        width_val = None

    # Use mobile layout only if width < 768; otherwise, use desktop layout.
    if width_val is not None and width_val < 768:
        layout_mode = "Mobile"
    else:
        layout_mode = "Desktop"

    #st.write("Layout mode:", layout_mode)

    completed_workouts_today = get_completed_workouts_today()
    workout_days = ["Day 1", "Day 2", "Day 3"]

    # Get all workouts to initialize weights
    all_workouts = []
    for day in workout_days:
        workouts = get_workout_template(day)
        for workout in workouts:
            workout['Day'] = day
            all_workouts.append(workout)

    # Get current weights from templates
    exercise_weights = {}
    for workout in all_workouts:
        exercise = workout['Exercise Name']
        if exercise not in exercise_weights:
            try:
                weight_val = float(workout['Weight'])
            except ValueError:
                weight_val = 0.0  # Default for non-numeric weights like 'BW'
            exercise_weights[exercise] = weight_val

    if layout_mode == "Mobile":
        # Define icons to represent each day.
        day_icons = {
            "Day 1": "🟣",
            "Day 2": "⚫",
            "Day 3": "🔵",
        }

        # Use 2-column grid in mobile view for better fit.
        num_cols = 2

        # Inject minimal CSS to tightly arrange the buttons.
        st.markdown(
            """
            <style>
            .stButton button {
                width: 100% !important;
                font-size: 0.8em !important;
                padding: 6px 4px !important;
                margin: 2px !important;
                border-radius: 6px;
            }
            </style>
            """, unsafe_allow_html=True
        )

        # Render the grid in groups of 2.
        for i in range(0, len(all_workouts), num_cols):
            cols = st.columns(num_cols)
            row_workouts = all_workouts[i:i+num_cols]
            for j in range(num_cols):
                if j < len(row_workouts):
                    workout = row_workouts[j]
                    exercise_name = workout['Exercise Name']
                    sets = workout['Sets']
                    reps = workout['Reps']
                    weight = exercise_weights[exercise_name]
                    day = workout['Day']
                    icon = day_icons.get(day, "")
                    button_key = f"{day}_{exercise_name}"

                    # Add a check mark if the exercise is already complete.
                    if exercise_name in completed_workouts_today:
                        button_label = f"✅ {exercise_name} {sets}x{reps} ({weight})"
                        disabled = True
                    else:
                        button_label = f"{icon} {exercise_name} {sets}x{reps} ({weight})"
                        disabled = False

                    with cols[j]:
                        if st.button(button_label, key=button_key, disabled=disabled, help=day):
                            save_workout_session({
                                'exercise': exercise_name,
                                'sets': workout['Sets'],
                                'reps': workout['Reps'],
                                'weight': exercise_weights[exercise_name],
                                'description': workout['Description']
                            })
                            # Refresh the app to reflect the new state.
                            streamlit_js_eval(js_expressions="parent.window.location.reload()")
                else:
                    cols[j].empty()
    else:
        # Desktop Layout: Simple workout tracker
        for workout in all_workouts:
            exercise_name = workout['Exercise Name']
            sets = workout['Sets']
            reps = workout['Reps']
            weight = exercise_weights[exercise_name]
            description = workout['Description']
            day = workout['Day']
            button_key = f"{day}_{exercise_name}"

            col1, col2, col3, col4 = st.columns(4)
            col1.write(f"**{exercise_name}**")
            col2.write(f"{sets} sets of {reps} reps ({weight} lbs)")
            col3.write(f"*{description}*")
            col4.write(f"Day: {day}")

            if exercise_name in completed_workouts_today:
                col4.button("✅ Completed", key=button_key, disabled=True)
            else:
                if col4.button("Mark as Complete", key=button_key):
                    save_workout_session({
                        'exercise': exercise_name,
                        'sets': sets,
                        'reps': reps,
                        'weight': weight,
                        'description': description
                    })
                    streamlit_js_eval(js_expressions="parent.window.location.reload()")

    st.text("Today is 2026-01-14-06")

if __name__ == "__main__":
    main()
