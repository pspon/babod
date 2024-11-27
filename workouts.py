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
    worksheet = sheet.worksheet(template_name)
    return worksheet.get_all_records()  # Returns a list of dictionaries

# Function to save the completed workout session to Google Sheets
def save_workout_session(workout):
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'  # Replace with your actual Google Sheet ID
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)
    session_worksheet = sheet.worksheet('Session Data')  # Name of the sheet where session data will be stored
    
    # Save the workout to the session sheet, including the timestamp
    session_worksheet.append_row([
        workout['timestamp'],  # Save the timestamp when the workout was completed
        workout['exercise'],
        workout['sets'],
        workout['reps'],
        workout['weight'],
        workout['completed'],
        workout['description']
    ])

# Function to display a specific day's workout template
def display_day_workout(day_name):
    # Fetch the selected workout template data
    workout_data = get_workout_template(day_name)
    st.write(f"### {day_name} Workout Template")

    # Get the Eastern Time timezone
    eastern = pytz.timezone('US/Eastern')

    for workout in workout_data:
        exercise_name = workout['Exercise Name']
        sets = workout['Sets']
        reps = workout['Reps']
        weight = workout['Weight']
        description = workout['Description']

        completed_key = f"completed_{day_name}_{exercise_name}"

        # Create a checkbox for each exercise
        completed = st.checkbox(
            f"{exercise_name} - {sets} sets of {reps} reps ({weight})",
            key=completed_key,
            value=st.session_state.get(completed_key, False)
        )

        if completed and not st.session_state.get(completed_key, False):
            # Save the workout details to the session sheet
            workout_details = {
                'timestamp': datetime.now(eastern).strftime('%Y-%m-%d %H:%M:%S'),
                'exercise': exercise_name,
                'sets': sets,
                'reps': reps,
                'weight': weight,
                'completed': True,
                'description': description
            }
            save_workout_session(workout_details)
            st.session_state[completed_key] = True
            st.experimental_rerun()  # Reload the page to reflect changes

# Streamlit app entry point
def main():
    st.title("Workout Tracker")

    # Set the default active day to "Day 1" if not already set
    if "active_day" not in st.session_state:
        st.session_state["active_day"] = "Day 1"

    # Create tabs for the workout templates
    tabs = st.tabs(["Day 1", "Day 2", "Day 3"])
    day_names = ["Day 1", "Day 2", "Day 3"]

    # Display the content of the active tab
    for i, tab in enumerate(tabs):
        with tab:
            if st.session_state["active_day"] == day_names[i]:
                display_day_workout(day_names[i])
                st.session_state["active_day"] = day_names[i]

if __name__ == "__main__":
    main()
