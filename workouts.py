import streamlit as st
from streamlit_js_eval import streamlit_js_eval
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz

# Function to authenticate with Google Sheets API
def authenticate_google_sheets():
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credential_json_string = st.secrets["barabod"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credential_json_string, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# Function to get workout data from the selected template
def get_workout_template(template_name):
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet(template_name)
    return worksheet.get_all_records()

# Function to fetch today's completed workouts
def get_completed_workouts_today():
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)
    session_worksheet = sheet.worksheet('Session Data')
    
    today = datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d')
    records = session_worksheet.get_all_records()
    return {record['exercise'] for record in records if record['timestamp'].startswith(today)}

# Function to save a completed workout
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

# Streamlit app entry point
def main():
    st.title("Workout Tracker")
    
    # Detect the viewport width using JavaScript.
    # For an iPhone SE, this should return something like 375.
    width = streamlit_js_eval(js_expressions="window.innerWidth", key="device_width")
    st.write("Detected window width:", width)
    
    # Try to convert the detected width to an integer.
    try:
        width_val = int(width)
    except Exception as e:
        width_val = None
    
    # Determine layout mode based on detected width,
    # or allow a manual override if detection fails.
    if width_val is not None:
        layout_mode = "Mobile" if width_val <= 768 else "Desktop"
    else:
        layout_mode = "Mobile" if st.sidebar.checkbox("Force Mobile Layout", value=False) else "Desktop"
    
    st.write("Layout mode:", layout_mode)
    
    # Inject mobile-specific CSS when in Mobile layout.
    if layout_mode == "Mobile":
        st.markdown(
            """
            <style>
            /* Card-style tile for each workout */
            .workout-tile {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                background-color: #f9f9f9;
            }
            /* Make buttons full-width and easier to tap */
            button {
                width: 100% !important;
                padding: 10px;
                font-size: 1.1em;
            }
            </style>
            """, unsafe_allow_html=True
        )
    
    completed_workouts_today = get_completed_workouts_today()
    workout_days = ["Day 1", "Day 2", "Day 3"]
    
    if layout_mode == "Mobile":
        # Mobile: Display workouts as full-width card tiles, grouped by day.
        for day in workout_days:
            st.subheader(day)
            workouts = get_workout_template(day)
            for workout in workouts:
                exercise_name = workout['Exercise Name']
                sets = workout['Sets']
                reps = workout['Reps']
                weight = workout['Weight']
                description = workout['Description']
                button_key = f"{day}_{exercise_name}"
                
                with st.container():
                    st.markdown("<div class='workout-tile'>", unsafe_allow_html=True)
                    st.write(f"**{exercise_name}**")
                    st.write(f"{sets} sets of {reps} reps ({weight})")
                    st.write(f"*{description}*")
                    
                    if exercise_name in completed_workouts_today:
                        st.button("✅ Completed", key=button_key, disabled=True)
                    else:
                        if st.button("Mark as Complete", key=button_key):
                            save_workout_session({
                                'exercise': exercise_name,
                                'sets': sets,
                                'reps': reps,
                                'weight': weight,
                                'description': description
                            })
                            # Reload the app to show the updated state.
                            streamlit_js_eval(js_expressions="parent.window.location.reload()")
                    st.markdown("</div>", unsafe_allow_html=True)
    else:
        # Desktop: Retain original four-column layout.
        all_workouts = []
        for day in workout_days:
            workouts = get_workout_template(day)
            for workout in workouts:
                workout['Day'] = day  # Attach day information.
                all_workouts.append(workout)
                
        for workout in all_workouts:
            exercise_name = workout['Exercise Name']
            sets = workout['Sets']
            reps = workout['Reps']
            weight = workout['Weight']
            description = workout['Description']
            day = workout['Day']
            button_key = f"{day}_{exercise_name}"
            
            col1, col2, col3, col4 = st.columns(4)
            col1.write(f"**{exercise_name}**")
            col2.write(f"{sets} sets of {reps} reps ({weight})")
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
    
    st.text("Today is 2025-02-08")

if __name__ == "__main__":
    main()
