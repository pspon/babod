import io
import streamlit as st
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

    # Access the appropriate worksheet based on the user's selection
    worksheet = sheet.worksheet(template_name)
    
    # Get all records (workout data) from the selected sheet
    data = worksheet.get_all_records()  # Returns a list of dictionaries
    return data

# Function to display the workout template within a tab
def display_workout_template(tab_name):
    # Fetch the workout template data
    workout_data = get_workout_template(tab_name)

    # Display the workout template with checkboxes for user interaction
    st.write(f"### {tab_name} Workout Template")

    # Track completed workouts
    completed_workouts = []

    for workout in workout_data:
        exercise_name = workout['Exercise Name']
        sets = workout['Sets']
        reps = workout['Reps']
        weight = workout['Weight']
        description = workout['Description']

        # Unique keys for checkboxes and timestamps
        completed_key = f"completed_{tab_name}_{exercise_name}"
        timestamp_key = f"timestamp_{tab_name}_{exercise_name}"

        # Create a checkbox for the exercise
        completed = st.checkbox(
            f"{exercise_name} - {sets} sets of {reps} reps ({weight})",
            key=completed_key,
            value=st.session_state.get(completed_key, False)
        )

        # Eastern timezone for timestamps
        eastern = pytz.timezone('US/Eastern')

        # If the checkbox is ticked, update session state with the timestamp
        if completed:
            if timestamp_key not in st.session_state:
                st.session_state[timestamp_key] = datetime.now(eastern).strftime('%Y-%m-%d %H:%M:%S')

            # Append to completed workouts
            completed_workouts.append({
                'exercise': exercise_name,
                'sets': sets,
                'reps': reps,
                'weight': weight,
                'completed': True,
                'description': description,
                'timestamp': st.session_state[timestamp_key]
            })
        else:
            # If unchecked, remove the timestamp from session state
            if timestamp_key in st.session_state:
                del st.session_state[timestamp_key]

    # Automatically save session data to Google Sheets when checkboxes are ticked
    if completed_workouts:
        save_workout_session(completed_workouts)

# Function to check if the workout has already been saved based on timestamp
def workout_exists(timestamp):
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'  # Replace with your actual Google Sheet ID
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)
    session_worksheet = sheet.worksheet('Session Data')  # Name of the sheet where session data will be stored

    # Get all records from the session data sheet and check if the timestamp already exists
    records = session_worksheet.get_all_records()
    for record in records:
        if record['timestamp'] == timestamp:
            return True  # The workout has already been saved
    
    return False  # The workout is new

# Function to save the completed workout session to Google Sheets
def save_workout_session(completed_workouts):
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'  # Replace with your actual Google Sheet ID
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)
    session_worksheet = sheet.worksheet('Session Data')  # Name of the sheet where session data will be stored

    # Save each completed workout to the session sheet, including the timestamp, if it doesn't exist
    for workout in completed_workouts:
        # Check if the workout with the same timestamp already exists
        if not workout_exists(workout['timestamp']):
            session_worksheet.append_row([
                workout['timestamp'],  # Save the timestamp when the workout was completed
                workout['exercise'],
                workout['sets'],
                workout['reps'],
                workout['weight'],
                workout['completed'],
                workout['description']
            ])

# Streamlit app entry point
def main():
    st.title("Workout Tracker")

    # Tabs for each workout day
    tabs = ["Day 1", "Day 2", "Day 3"]

    # Remember the last opened tab across reloads
    if "active_tab_index" not in st.session_state:
        st.session_state["active_tab_index"] = 0  # Default to the first tab

    # Create tabs
    tab_objects = st.tabs(tabs)

    # Display content based on the selected tab
    for index, tab_name in enumerate(tabs):
        with tab_objects[index]:
            if index == st.session_state["active_tab_index"]:
                st.session_state["active_tab_index"] = index  # Save the active tab index
            display_workout_template(tab_name)
    st.text("Today is 2024-12-05")

if __name__ == "__main__":
    main()
