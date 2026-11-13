# EmpowerHer: Setup and Run

One command sets up and starts the whole project. EmpowerHer's frontend (the HTML pages) is served by the same Django server as the API, so there is only one thing to start.

## 0. The quickest way: Docker

If you have Docker, one command runs EmpowerHer with PostgreSQL, exactly as it would run on a server:

```bash
docker compose up --build
```

Then open http://localhost:8000 (demo login below). What runs:

| Service | What it does |
| --- | --- |
| `db` | PostgreSQL 17; data in the `db-data` volume |
| `web` | EmpowerHer on gunicorn, debug off. On first start it generates the secret and encryption keys into the `app-data` volume, applies migrations and creates the demo account |
| `scheduler` | Runs `send_scheme_alerts` once a day |

**Back up both volumes together:** the keys in `app-data` are needed to read the encrypted data in `db-data`. Stop with `docker compose down` (add `-v` only if you want to delete all data). Run a command inside with e.g. `docker compose exec web python manage.py seed_demo`.

No Docker Desktop? On a Mac, the free command-line route is the official `docker` CLI plus [Colima](https://github.com/abiosoft/colima): `colima start`, then the command above.

## 1. Requirements

- **Python 3.11, 3.12 or 3.13** from https://www.python.org/downloads/
  - On Windows, tick **"Add python.exe to PATH"** during installation.
- About **1.5 GB** of free disk space, for the packages and the OCR models.
- An internet connection for the first run only, to download packages.

Nothing else is needed. There is no Node.js, no database server and no Tesseract.

## 2. Set up and run

**macOS / Linux**, from the project folder:

```bash
./setup.sh
```

**Windows**: double-click `setup.bat`, or from Command Prompt in the project folder:

```bat
setup.bat
```

The first run takes 2–5 minutes. Your browser then opens **http://localhost:8000**. Stop the server with **Ctrl + C**.

Later runs use the same command and start in a few seconds. Existing packages, keys and data are kept.

### What the script does

| Step | Action |
| --- | --- |
| 1 | Finds a supported Python version |
| 2 | Creates a virtual environment in `.venv/` |
| 3 | Installs the packages from `empowerher/backend/requirements.txt` |
| 4 | Creates `empowerher/backend/.env` with new random encryption keys (only if it does not exist) |
| 5 | Builds the processed datasets if they are missing, and creates or updates the database (`migrate`) |
| 6 | Creates the demo account; runs the tests if `--test` is given |
| 7 | Starts the server and opens the browser |

### Options

| Option | Effect |
| --- | --- |
| `--test` | Run the automated tests (127 tests) before starting |
| `--no-run` | Set up only; don't start the server |
| `--no-demo` | Don't create or reset the demo account |
| `PORT=8080 ./setup.sh` (macOS/Linux) or `set PORT=8080` then `setup.bat` (Windows) | Use a different port |

## 3. Log in

- **Demo account**: username `demo_entrepreneur`, password `EmpowerHer@Demo2026`.
  - It is a local demo account with sample data: two validated ideas (one confidential), an Idea Vault entry and a verified sample PAN document.
  - To use a different password, set `DEMO_PASSWORD` before running the script.
  - Running the script again resets this account.
- **Your own account**: click **Register** on the home page.
- **Admin panel** (optional): run the command below, then open http://localhost:8000/admin/

```bash
.venv/bin/python empowerher/backend/manage.py createsuperuser
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

## 4. Pages to try

| Page | URL |
| --- | --- |
| Home | http://localhost:8000/ |
| Dashboard | http://localhost:8000/dashboard/ |
| Business Idea Validation | http://localhost:8000/business/validation/ |
| Government Schemes | http://localhost:8000/schemes/ |
| Funding & Loans (EMI, private HE check) | http://localhost:8000/funding/ |
| Local Market Demand | http://localhost:8000/market/ |
| Document Verification | http://localhost:8000/documents/ |
| Idea Vault (ZKP) | http://localhost:8000/vault/ |
| Verify a proof (public) | http://localhost:8000/vault/verify/ |
| AI Assistant (voice in Chrome / Edge) | http://localhost:8000/assistant/ |
| Women Safety | http://localhost:8000/safety/ |
| Profile | http://localhost:8000/profile/ |

## 5. Optional: AI answers

Without an API key, the assistant and recommendations use EmpowerHer's own data. To enable AI answers, put an OpenAI key in `empowerher/backend/.env`:

```
OPENAI_API_KEY=sk-...
```

Then restart the server.

## 6. Important: back up `.env`

`empowerher/backend/.env` holds the encryption keys for Idea Vault ideas, confidential ideas and uploaded documents.
- **If it is lost**, that data can never be decrypted.
- **Never commit it or share it.** It is already excluded from git.
- **Each computer gets its own keys** when it runs the setup, so copying `db.sqlite3` to another machine also requires copying `.env`.

## 7. Production deployment (Linux server)

The steps above run EmpowerHer in development mode. To run it for real users:

1. **Install on a Linux server** (or macOS) with Python 3.11–3.13, then run `./setup.sh --no-run --no-demo`.
2. **Configure production.** In `empowerher/backend/.env`, set the values from `empowerher/backend/.env.production.example`:
   - `DJANGO_DEBUG=False`
   - a new long `DJANGO_SECRET_KEY`
   - your domain in `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` and `DJANGO_CORS_ALLOWED_ORIGINS`
   - `DJANGO_BEHIND_PROXY=True`
   - `DATABASE_URL` for PostgreSQL (recommended; see below)

   **Keep the existing encryption keys.**
3. **Start the app:**
   ```bash
   ./run_production.sh
   ```
   It checks the configuration (`check --deploy`), applies migrations, collects static files, and starts **gunicorn** on port 8000 (`PORT` and `WORKERS` can be changed).
4. **Put HTTPS in front.** Use a reverse proxy (nginx, Caddy, or your hosting provider's) to terminate HTTPS and forward to port 8000.

What production mode turns on:
- HTTPS redirect, HSTS, secure cookies and `X-Frame-Options: DENY`;
- compressed, cache-busting static files (WhiteNoise);
- a JSON-only API, and CORS limited to your domain;
- refusal to start without a real secret key;
- rate limits (login, AI, uploads) shared across all workers.

SQLite is fine for a small deployment. For many concurrent users, use PostgreSQL: create a database and set
`DATABASE_URL=postgres://user:password@host:5432/empowerher` in `.env`; `run_production.sh` then creates the tables in it. (The driver, `psycopg`, is already in `requirements.txt`.) Back up the database and `.env` together, since the encryption keys in `.env` are needed to read the data.

**Debug mode is off by default.** If `DJANGO_DEBUG` is missing, EmpowerHer runs in production mode and refuses to start without a real `DJANGO_SECRET_KEY`. The setup scripts write `DJANGO_DEBUG=True` into your local `.env`, so this only matters on a server.

### Scheme alerts

Users see alerts on the Schemes page and a badge on the dashboard. To create them for everyone (not only when a user opens the page), run this once a day, e.g. from cron:

```bash
python manage.py send_scheme_alerts
```

A scheme can carry an optional `"deadline": "YYYY-MM-DD"` in `datasets/curated/schemes.json`; matching users are alerted 30 days before.

### DigiLocker verification (optional)

DigiLocker lets users confirm, with their consent, that an uploaded PAN matches the one issued by the Income Tax Department. It needs EmpowerHer to be registered as a DigiLocker **Requester** partner on [API Setu](https://apisetu.gov.in/), which gives a client ID and secret. Then set in `.env`:

```
DIGILOCKER_CLIENT_ID=...
DIGILOCKER_CLIENT_SECRET=...
DIGILOCKER_REDIRECT_URI=https://your-domain/api/documents/digilocker/callback/
# Only if DigiLocker gives you a different base URL (e.g. a sandbox):
DIGILOCKER_BASE_URL=https://api.digitallocker.gov.in/public/oauth2
```

Register the same redirect URI with DigiLocker. Without these values the Documents page explains that DigiLocker isn't switched on.

### Checks for developers

```bash
pip install -r requirements-dev.txt     # ruff + coverage
ruff check .                            # lint (also runs on GitHub)
coverage run manage.py test && coverage report
python3 ../../scripts/smoke_test.py http://localhost:8000   # against a running server
```

## 8. Troubleshooting

| Problem | Fix |
| --- | --- |
| `Python 3.11, 3.12 or 3.13 is required` | Install Python 3.12 from python.org, then run the script again |
| `Permission denied: ./setup.sh` | Run `chmod +x setup.sh` once |
| `That port is already in use` | Stop the other server, or use `PORT=8080 ./setup.sh` |
| Browser shows "can't connect" right after start (Windows) | Wait a few seconds and refresh |
| Package install fails behind a proxy or firewall | Connect to an open network for the first run |
| `Set the IDEA_VAULT_ENCRYPTION_KEY environment variable` | `.env` is missing or incomplete; restore your backup. On a fresh install with no data, delete `.env` and rerun the script |
| Voice input button is greyed out | Use Chrome or Edge; Firefox has no speech recognition |
