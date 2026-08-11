#!/usr/bin/env python3
"""One-time migration: copy the Google Sheet into the local SQLite database.

Run this once on the machine that still has the service-account credentials,
then copy ``data/babod.db`` to the Raspberry Pi (or run it on the Pi itself).

    pip install -r requirements-import.txt
    python scripts/import_from_sheets.py --credentials service_account.json

Credentials are read from ``--credentials`` (a service-account JSON file) or,
if omitted, from the ``[barabod]`` table in ``.streamlit/secrets.toml`` — the
same place the old Streamlit Cloud app read them from.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storage  # noqa: E402

DEFAULT_SHEET_ID = "1xkPGxluU_EYHz0eWPXnzq-VZMVedl-hgqzeEVp6eLTU"
DEFAULT_DAYS = ["Day 1", "Day 2", "Day 3"]
SESSION_TAB = "Session Data"
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def load_credentials(path):
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    try:
        import tomllib
    except ModuleNotFoundError:  # Python < 3.11
        import tomli as tomllib

    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        raise SystemExit(
            "No credentials given and .streamlit/secrets.toml not found. "
            "Pass --credentials /path/to/service_account.json"
        )
    with open(secrets_path, "rb") as handle:
        secrets = tomllib.load(handle)
    if "barabod" not in secrets:
        raise SystemExit("secrets.toml has no [barabod] section")
    return secrets["barabod"]


def open_sheet(credentials, sheet_id):
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials, scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(sheet_id)


def import_templates(sheet, days):
    imported = 0
    for day in days:
        try:
            worksheet = sheet.worksheet(day)
        except Exception as error:  # noqa: BLE001 - tab may simply not exist
            print(f"  skipping {day}: {error}")
            continue

        for position, record in enumerate(worksheet.get_all_records()):
            name = str(record.get("Exercise Name", "")).strip()
            if not name:
                continue
            storage.upsert_exercise(
                day=day,
                name=name,
                sets=record.get("Sets", "3"),
                reps=record.get("Reps", "10"),
                weight=record.get("Weight", 0),
                description=record.get("Description", ""),
                position=position,
            )
            imported += 1
        print(f"  {day}: {imported} exercises so far")
    return imported


def import_sessions(sheet):
    try:
        worksheet = sheet.worksheet(SESSION_TAB)
    except Exception as error:  # noqa: BLE001
        print(f"  skipping '{SESSION_TAB}': {error}")
        return 0

    existing = {(row["timestamp"], row["exercise"]) for row in storage.all_sessions()}
    imported = 0
    for record in worksheet.get_all_records():
        values = list(record.values())
        timestamp = str(record.get("timestamp") or (values[0] if values else "")).strip()
        exercise = str(record.get("exercise") or (values[1] if len(values) > 1 else "")).strip()
        if not timestamp or not exercise:
            continue
        if (timestamp, exercise) in existing:  # re-running is safe
            continue
        storage.log_workout(
            exercise=exercise,
            sets=record.get("sets", ""),
            reps=record.get("reps", ""),
            weight=record.get("weight", 0),
            description=record.get("description", ""),
            timestamp=timestamp,
        )
        existing.add((timestamp, exercise))
        imported += 1
    return imported


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", help="Service-account JSON file")
    parser.add_argument("--sheet-id", default=DEFAULT_SHEET_ID)
    parser.add_argument(
        "--days", nargs="*", default=DEFAULT_DAYS, help="Template tab names"
    )
    parser.add_argument(
        "--skip-sessions", action="store_true", help="Import the plan only"
    )
    args = parser.parse_args()

    storage.init_db(seed_if_empty=False)
    print(f"Writing to {storage.db_path()}")

    sheet = open_sheet(load_credentials(args.credentials), args.sheet_id)

    print("Importing workout templates…")
    exercises = import_templates(sheet, args.days)

    sessions = 0
    if not args.skip_sessions:
        print("Importing session history…")
        sessions = import_sessions(sheet)

    print(f"Done: {exercises} exercises, {sessions} logged sessions.")


if __name__ == "__main__":
    main()
