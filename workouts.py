import io
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import toml
import json

# Function to authenticate with Google Sheets API
def authenticate_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    #creds = ServiceAccountCredentials.from_json_keyfile_name('babod.json', scope)
    credential_json_string = st.secrets["barabod"]
    st.write(credential_json_string)
    # Create a file-like object from the JSON string
    json_file = io.StringIO(credential_json_string)
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_file, scope)
    #st.write(secret)
    #st.write(type(secret))
    #toml_string = toml.loads(st.secrets["barabod"])
    #creds = json.dumps(toml_string, indent=4)
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

# Function to display and interact with the workout template
def display_workout_template():
    # User selects which template to use for the workout session
    template_choice = st.selectbox("Select Workout Template", ["Day 1", "Day 2", "Day 3"], key="template_choice")

    # Clear the cache if template is switched
    if template_choice != st.session_state.get("last_template", None):
        st.session_state.clear()  # Clears the session state (including checkbox and timestamp data)

    # Update the last selected template in session state
    st.session_state["last_template"] = template_choice

    # Fetch the selected workout template data
    workout_data = get_workout_template(template_choice)

    # Display the workout template with checkboxes for user interaction
    st.write(f"### {template_choice} Workout Template")

    completed_workouts = []
    for workout in workout_data:
        exercise_name = workout['Exercise Name']
        sets = workout['Sets']
        reps = workout['Reps']
        weight = workout['Weight']
        description = workout['Description']

        # Use session_state to keep track of checkbox and timestamp
        completed_key = f"completed_{exercise_name}"

        # Check if the exercise has been marked as completed
        completed = st.checkbox(f"{exercise_name} - {sets} sets of {reps} reps ({weight})", 
                                key=exercise_name,
                                value=st.session_state.get(completed_key, False))  # Restore state of checkbox from session_state

        # If the checkbox is checked, save the timestamp in session state
        if completed:
            timestamp_key = f"timestamp_{exercise_name}"
            # Save the timestamp only if it's checked
            if timestamp_key not in st.session_state:
                st.session_state[timestamp_key] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            completed_workouts.append({
                'exercise': exercise_name,
                'sets': sets,
                'reps': reps,
                'weight': weight,
                'completed': True,
                'description': description,
                'timestamp': st.session_state[timestamp_key]  # Use the timestamp from session state
            })
            # Save the checkbox state in session_state
            st.session_state[completed_key] = True
        else:
            # Ensure that if the checkbox is unchecked, the timestamp is removed from session_state
            timestamp_key = f"timestamp_{exercise_name}"
            if timestamp_key in st.session_state:
                del st.session_state[timestamp_key]
            st.session_state[completed_key] = False

    # Button to save the completed workout session
    if st.button("Save Workout Session"):
        save_workout_session(completed_workouts)
        st.success("Workout session saved successfully!")

# Function to save the completed workout session to Google Sheets
def save_workout_session(completed_workouts):
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'  # Replace with your actual Google Sheet ID
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)
    session_worksheet = sheet.worksheet('Session Data')  # Name of the sheet where session data will be stored
    
    # Save each completed workout to the session sheet, including the timestamp
    for workout in completed_workouts:
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
    display_workout_template()

if __name__ == "__main__":
    main()
