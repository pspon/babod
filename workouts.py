import streamlit as st
from streamlit_js_eval import streamlit_js_eval
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz

# Function to authenticate with Google Sheets API
def authenticate_google_sheets():
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credential_json_string = st.secrets["barabod"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credential_json_string, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# Function to get workout data from the selected template (Day 1, Day 2, or Day 3)
def get_workout_template(template_name):
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'  # Replace with your actual Google Sheet ID
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet(template_name)
    return worksheet.get_all_records()

# Function to fetch today's completed workouts from the session sheet
def get_completed_workouts_today():
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)
    session_worksheet = sheet.worksheet('Session Data')
    
    today = datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d')
    records = session_worksheet.get_all_records()
    return {record['exercise'] for record in records if record['timestamp'].startswith(today)}

# Function to save a completed workout to the session sheet
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
        True,  # Completed
        workout['description']
    ])

# Function to display the workout template with buttons
def display_workout_template(tab_name):
    st.write(f"### {tab_name} Workout Template")
    workout_data = get_workout_template(tab_name)
    completed_workouts_today = get_completed_workouts_today()
    
    for workout in workout_data:
        exercise_name = workout['Exercise Name']
        sets = workout['Sets']
        reps = workout['Reps']
        weight = workout['Weight']
        description = workout['Description']
        
        button_key = f"{tab_name}_{exercise_name}"
        if exercise_name in completed_workouts_today:
            st.button(
                f"✅ {exercise_name} - {sets} sets of {reps} reps ({weight}) [Completed]",
                key=button_key,
                disabled=True
            )
        else:
            if st.button(f"{exercise_name} - {sets} sets of {reps} reps ({weight})", key=button_key):
                save_workout_session({
                    'exercise': exercise_name,
                    'sets': sets,
                    'reps': reps,
                    'weight': weight,
                    'description': description
                })
                streamlit_js_eval(js_expressions="parent.window.location.reload()")

# Streamlit app entry point
def main():
    st.title("Workout Tracker")
    tabs = ["Day 1", "Day 2", "Day 3"]
    if "active_tab_index" not in st.session_state:
        st.session_state["active_tab_index"] = 0

    tab_objects = st.tabs(tabs)
    for index, tab_name in enumerate(tabs):
        with tab_objects[index]:
            if index == st.session_state["active_tab_index"]:
                st.session_state["active_tab_index"] = index
            display_workout_template(tab_name)
    st.text("Today is 2024-12-30")

if __name__ == "__main__":
    main()
