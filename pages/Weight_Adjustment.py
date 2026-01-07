import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz

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

# Update weight in the template sheet.
def update_workout_weight(exercise_name, new_weight):
    sheet_id = '1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU'
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id)

    # Check each day for the exercise
    workout_days = ["Day 1", "Day 2", "Day 3"]
    for day in workout_days:
        worksheet = sheet.worksheet(day)
        records = worksheet.get_all_records()
        for i, record in enumerate(records):
            if record.get('Exercise Name') == exercise_name:
                # Update the weight (assuming column is 'Weight')
                row_num = i + 2  # +1 for 0-index, +1 for header
                worksheet.update_cell(row_num, 4, str(new_weight))  # Column D is Weight
                # Clear cache so fresh data is loaded
                get_workout_template.clear()
                break

def main():
    st.title("🏋️ Weight Adjustment - Progressive Training")

    workout_days = ["Day 1", "Day 2", "Day 3"]

    # Get all workouts to initialize weights
    all_workouts = []
    for day in workout_days:
        workouts = get_workout_template(day)
        for workout in workouts:
            workout['Day'] = day
            all_workouts.append(workout)

    # Initialize session state for weights if not present
    if 'weights' not in st.session_state:
        st.session_state.weights = {}
    if 'old_weights' not in st.session_state:
        st.session_state.old_weights = {}

    for workout in all_workouts:
        exercise = workout['Exercise Name']
        if exercise not in st.session_state.weights:
            try:
                weight_val = float(workout['Weight'])
            except ValueError:
                weight_val = 0.0  # Default for non-numeric weights like 'BW'
            st.session_state.weights[exercise] = weight_val
            st.session_state.old_weights[exercise] = weight_val

    st.write("Adjust the weights for each exercise. These changes will be saved to Google Sheets and used for future sessions.")

    # Group exercises by day
    exercises_by_day = {}
    for workout in all_workouts:
        day = workout['Day']
        exercise = workout['Exercise Name']
        if day not in exercises_by_day:
            exercises_by_day[day] = []
        if exercise not in [ex['name'] for ex in exercises_by_day[day]]:
            exercises_by_day[day].append({
                'name': exercise,
                'sets': workout['Sets'],
                'reps': workout['Reps'],
                'description': workout['Description']
            })

    # Display weight adjustment interface by day
    for day in workout_days:
        if day in exercises_by_day:
            with st.expander(f"📅 {day}", expanded=True):
                st.write(f"**{day} Workout**")
                for exercise_info in exercises_by_day[day]:
                    exercise = exercise_info['name']
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.write(f"**{exercise}**")
                        st.caption(f"{exercise_info['sets']} sets × {exercise_info['reps']} reps")
                        if exercise_info['description']:
                            st.caption(f"*{exercise_info['description']}*")
                    with col2:
                        st.write("Current:")
                        st.write(f"**{st.session_state.weights[exercise]} lbs**")
                    with col3:
                        new_weight = st.number_input(
                            "New Weight (lbs)",
                            min_value=0.0,
                            value=st.session_state.weights[exercise],
                            step=5.0,
                            key=f"weight_{exercise}_{day}"
                        )
                        if new_weight != st.session_state.weights[exercise]:
                            st.session_state.weights[exercise] = new_weight

    # Update Google Sheets if weights changed
    weights_changed = False
    for exercise in st.session_state.weights:
        if st.session_state.weights[exercise] != st.session_state.old_weights.get(exercise, st.session_state.weights[exercise]):
            update_workout_weight(exercise, st.session_state.weights[exercise])
            st.session_state.old_weights[exercise] = st.session_state.weights[exercise]
            weights_changed = True

    if weights_changed:
        st.success("✅ Weights updated successfully in Google Sheets!")

    # Show summary
    st.markdown("---")
    st.subheader("📊 Weight Summary")
    summary_data = []
    for day in workout_days:
        if day in exercises_by_day:
            st.write(f"**{day}:**")
            day_exercises = exercises_by_day[day]
            for exercise_info in day_exercises:
                exercise = exercise_info['name']
                weight = st.session_state.weights[exercise]
                st.write(f"• {exercise}: {weight} lbs")

if __name__ == "__main__":
    main()