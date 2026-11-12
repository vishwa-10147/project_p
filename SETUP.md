# EmpowerHer: Setup and Run

One command sets up and starts the whole project. EmpowerHer's frontend (the HTML pages) is served by the same Django server as the API, so there is only one thing to start.

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
| `--test` | Run the automated tests (49 tests) before starting |
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

## 7. Troubleshooting

| Problem | Fix |
| --- | --- |
| `Python 3.11, 3.12 or 3.13 is required` | Install Python 3.12 from python.org, then run the script again |
| `Permission denied: ./setup.sh` | Run `chmod +x setup.sh` once |
| `That port is already in use` | Stop the other server, or use `PORT=8080 ./setup.sh` |
| Browser shows "can't connect" right after start (Windows) | Wait a few seconds and refresh |
| Package install fails behind a proxy or firewall | Connect to an open network for the first run |
| `Set the IDEA_VAULT_ENCRYPTION_KEY environment variable` | `.env` is missing or incomplete; restore your backup. On a fresh install with no data, delete `.env` and rerun the script |
| Voice input button is greyed out | Use Chrome or Edge; Firefox has no speech recognition |
