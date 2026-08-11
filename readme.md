# Workout Tracker

A phone-friendly Streamlit workout tracker that runs on your own hardware. The
workout plan and every logged set live in a **local SQLite file** — no Google
Sheets, no cloud account, nothing leaves the Raspberry Pi.

## Features

- **Mobile-first UI** — full-width tap targets, cards that fit a phone screen,
  and a day picker that opens on the workout you're due for.
- **One tap to log**, one tap to undo a mistap.
- **Weights inline** — bump a weight from the exercise card mid-workout; it
  applies everywhere that exercise appears.
- **Plan & Weights page** to add, edit, and remove exercises and days.
- **History page** with per-day charts, per-exercise totals, and a CSV export.
- **Local storage** in `data/babod.db`, backed up with one command.

## Run it with Docker (Raspberry Pi)

Requires a 64-bit OS (Raspberry Pi OS 64-bit / Ubuntu) and Docker with the
Compose plugin: `curl -fsSL https://get.docker.com | sh` then
`sudo apt install docker-compose-plugin`.

```bash
git clone https://github.com/pspon/babod.git
cd babod
mkdir -p data                 # the database lands here, on the Pi's disk
docker compose up -d --build
```

Open `http://<pi-hostname>.local:8501` (or the Pi's IP) from your phone on the
same network. On iOS, *Share → Add to Home Screen* gives it an app icon and a
full-screen launch.

Useful commands:

```bash
docker compose logs -f        # tail logs
docker compose restart        # restart after a config change
docker compose down           # stop (data in ./data is untouched)
git pull && docker compose up -d --build   # update
```

The container runs as uid 1000 (the default `pi` user). If the host `data`
directory belongs to someone else, fix it once with
`sudo chown -R 1000:1000 data`.

### Configuration

| Variable | Default | What it does |
| --- | --- | --- |
| `BABOD_DB_PATH` | `/data/babod.db` in Docker, `data/babod.db` locally | SQLite file location |
| `BABOD_TIMEZONE` | `US/Eastern` | Timezone for timestamps and "today" |
| `BABOD_SEED_FILE` | `seed/template.json` | Starter plan for an empty database |

Set the timezone in an `.env` file next to `docker-compose.yml`:

```
BABOD_TIMEZONE=US/Eastern
```

Theme, port, and other Streamlit settings live in `.streamlit/config.toml`.

## Run it without Docker

```bash
pip install -r requirements.txt
streamlit run app.py
```

The database is created on first run and seeded from `seed/template.json`,
which is a placeholder plan — replace it on the **Plan & Weights** page or by
importing your old sheet.

## Migrating from Google Sheets

The old version read the plan and session history from a Google Sheet. To move
that data into the local database, run this once on a machine that still has
the service-account credentials:

```bash
pip install -r requirements-import.txt
python scripts/import_from_sheets.py --credentials service_account.json
```

It reads the `Day 1`/`Day 2`/`Day 3` tabs plus `Session Data`, skips rows it
already imported (so re-running is safe), and writes to `BABOD_DB_PATH`. If you
run it on your laptop, copy the resulting `data/babod.db` to the Pi's `data/`
directory before starting the container. Without `--credentials` it falls back
to the `[barabod]` section of `.streamlit/secrets.toml`.

## Backups

The database is one file, but it uses WAL mode, so copy it with the backup
script rather than `cp`:

```bash
python scripts/backup_db.py --db data/babod.db --out ~/babod-backups
```

Nightly, via `crontab -e` on the Pi:

```
0 3 * * * /usr/bin/python3 /home/pi/babod/scripts/backup_db.py --db /home/pi/babod/data/babod.db --out /home/pi/babod-backups
```

The History page also has a **Download all sessions (CSV)** button for a copy
you can open in a spreadsheet.

## Layout

```
app.py                        Today's workout — the main screen
ui.py                         Shared page setup and mobile styling
storage.py                    SQLite data layer (all reads and writes)
pages/1_Plan_and_Weights.py   Edit the plan and working weights
pages/2_History.py            Charts, log table, CSV export
seed/template.json            Starter plan for a fresh database
scripts/import_from_sheets.py One-time Google Sheets migration
scripts/backup_db.py          Consistent database snapshots
Dockerfile, docker-compose.yml
```
