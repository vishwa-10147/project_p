<div align="center">

<img src="docs/assets/logo.svg" alt="EmpowerHer logo" width="128" height="128">

# EmpowerHer

**Empowering women. Protecting ideas. Building futures.**

A privacy-preserving AI platform that helps women entrepreneurs in India validate business ideas,<br>
find government schemes and funding, and protect their ideas and documents with real cryptography.

[![Tests](https://github.com/vishwa-10147/project_p/actions/workflows/tests.yml/badge.svg)](https://github.com/vishwa-10147/project_p/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.11%20–%203.13-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-0C4B33?logo=django&logoColor=white)
![Tests](https://img.shields.io/badge/tests-127-8e3b9d)
![Coverage](https://img.shields.io/badge/coverage-85%25-8e3b9d)
![Languages](https://img.shields.io/badge/languages-7%20Indian%20languages-8e3b9d)
![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[Features](#-features) · [Screenshots](#-screenshots) · [Quick start](#-quick-start) · [How privacy works](#-how-your-data-is-protected) · [Project docs](#-documentation)

</div>

---

## ✨ Features

| | Module | What it does |
| :---: | --- | --- |
| 💡 | **Business idea validation** | Financial estimate, strengths and risks, census market indicators, matching schemes and optional AI advice. A 🔒 **Confidential** mode encrypts the idea's description. |
| 🏛️ | **Government schemes** | 25 curated central and state schemes, with a rule-based + TF-IDF recommender that explains *why* each one fits. Schemes whose validity ended or is pending renewal are clearly flagged. |
| 🔔 | **Scheme alerts** | Tells you when a new scheme matching your profile is added, or a matching scheme's deadline is under 30 days away. |
| 💰 | **Funding tools** | EMI with full amortisation, loan affordability, PMEGP subsidy calculator and loan routes. |
| 🧮 | **Private loan check** | Checks loan affordability using **Paillier homomorphic encryption**: the server computes on income figures it never sees. |
| 📊 | **Market analysis** | District-level demand index for each business category (Census 2011) plus each state's women-MSME ecosystem. |
| 📄 | **Document verification** | OCR for PAN, Aadhaar, GSTIN, Udyam and IFSC, with checksum validation, masked ID numbers and encrypted storage. **DigiLocker** confirmation for PAN, ready once the server is a registered DigiLocker partner. |
| 🔐 | **Idea Vault** | **End-to-end encrypted in your browser** with your own passphrase: not even the server can read it. Pedersen commitments let you prove an idea is yours with a **zero-knowledge proof**, without revealing it. |
| 💬 | **Multilingual assistant** | English, Telugu, Hindi, Tamil, Kannada, Marathi and Bengali, by text or voice. Works offline from a knowledge base; OpenAI is optional. |
| 🛡️ | **Safety** | National and state helplines, reporting portals and safety guides, open to everyone without login. |
| 👤 | **Your data, your control** | Download all your data as JSON, change your password, or permanently delete your account. |
| 📱 | **Installable app** | Add EmpowerHer to your phone's home screen. Safety helplines and calculators keep working on a poor connection. |

## 📸 Screenshots

<table>
  <tr>
    <td width="50%"><img src="report/results/screenshots/02_dashboard.png" alt="Dashboard"><br><sub><b>Dashboard</b>: every module in one place</sub></td>
    <td width="50%"><img src="report/results/screenshots/03_validation_report.png" alt="Business validation report"><br><sub><b>Business validation</b>: report with finances, risks and market fit</sub></td>
  </tr>
  <tr>
    <td><img src="report/results/screenshots/04_scheme_recommendations.png" alt="Scheme recommendations"><br><sub><b>Schemes</b>: personalised recommendations with reasons</sub></td>
    <td><img src="report/results/screenshots/06_private_he_check.png" alt="Private homomorphic check"><br><sub><b>Private check</b>: loan affordability on encrypted figures</sub></td>
  </tr>
  <tr>
    <td><img src="report/results/screenshots/07_market_summary.png" alt="Market analysis"><br><sub><b>Market</b>: district demand index</sub></td>
    <td><img src="report/results/screenshots/10_document_verification.png" alt="Document verification"><br><sub><b>Documents</b>: OCR, checksums and masked IDs</sub></td>
  </tr>
  <tr>
    <td><img src="report/results/screenshots/12_vault_proof.png" alt="Idea Vault proof"><br><sub><b>Idea Vault</b>: zero-knowledge proof of ownership</sub></td>
    <td><img src="report/results/screenshots/14_assistant_multilingual.png" alt="Multilingual assistant"><br><sub><b>Assistant</b>: answers in 7 Indian languages</sub></td>
  </tr>
</table>

<details>
<summary>More screenshots</summary>

| | |
| --- | --- |
| ![Home](report/results/screenshots/01_home.png) | ![EMI calculator](report/results/screenshots/05_emi_calculator.png) |
| ![Safety](report/results/screenshots/15_safety.png) | ![Account controls](report/results/screenshots/17_account_controls.png) |

</details>

## 🚀 Quick start

**Option 1: Docker** (app + PostgreSQL, nothing else to install besides Docker):

```bash
docker compose up --build
```

Open **http://localhost:8000** and log in as `demo_entrepreneur` / `EmpowerHer@Demo2026`. Encryption keys are generated on first start and kept in the `app-data` volume.

**Option 2: Python 3.11 – 3.13** on your computer. One command sets everything up and starts the app:

```bash
./setup.sh          # macOS / Linux
```

```bat
setup.bat           :: Windows
```

The script creates a virtual environment, installs packages, generates encryption keys in `empowerher/backend/.env`, prepares the database and datasets, creates a demo account, and opens **http://localhost:8000**.

See **[SETUP.md](SETUP.md)** for options, troubleshooting and production deployment.

<details>
<summary><b>Useful commands</b></summary>

Run these from `empowerher/backend` with the virtual environment's Python:

| Command | Purpose |
| --- | --- |
| `python manage.py test` | Run the 127 automated tests (GitHub Actions also runs them on every push, on SQLite and PostgreSQL) |
| `coverage run manage.py test && coverage report` | Test coverage (needs `pip install -r requirements-dev.txt`) |
| `ruff check .` | Lint: style problems, likely bugs and security issues |
| `python manage.py seed_demo` | Create or reset the demo account |
| `python manage.py send_scheme_alerts` | Check scheme alerts for everyone (run daily; Docker's `scheduler` service does this) |
| `python3 scripts/smoke_test.py http://localhost:8000` | End-to-end check of a running server (from the project root) |
| `python manage.py run_benchmarks` | Measure performance (results in `report/results/benchmarks.json`) |
| `python datasets/build_datasets.py` | Rebuild the processed datasets from the raw downloads |

</details>

<details>
<summary><b>Environment variables</b> (<code>empowerher/backend/.env</code>)</summary>

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_DEBUG` | `True` for local development (setup writes this). **Off by default** |
| `IDEA_VAULT_ENCRYPTION_KEY` | Encrypts Idea Vault ideas and confidential business ideas (Fernet) |
| `DOCUMENT_ENCRYPTION_KEY` | Encrypts uploaded documents and their OCR text (Fernet) |
| `DATABASE_URL` | Optional, e.g. `postgres://user:pass@host:5432/empowerher`; SQLite when unset |
| `OPENAI_API_KEY` | Optional. Enables AI recommendations and AI assistant answers |
| `OPENAI_MODEL` | Optional, default `gpt-4.1-mini` |
| `DJANGO_TOKEN_TTL_HOURS` | Optional, login session lifetime (default 168 = 7 days) |
| `DJANGO_AUTH_RATE` | Optional, login/registration rate limit (default `10/minute`) |
| `DJANGO_AI_RATE` | Optional, AI assistant and idea validation limit per user (default `20/minute`) |
| `DJANGO_UPLOAD_RATE` | Optional, document upload (OCR) limit per user (default `10/minute`) |
| `DIGILOCKER_CLIENT_ID`, `DIGILOCKER_CLIENT_SECRET`, `DIGILOCKER_REDIRECT_URI` | Optional. Switch on DigiLocker verification (needs DigiLocker partner registration; see SETUP.md) |

For production (`DJANGO_DEBUG=False`, your domain, HTTPS), see `empowerher/backend/.env.production.example` and the production section of [SETUP.md](SETUP.md). `./run_production.sh` starts gunicorn.

> [!WARNING]
> Losing an encryption key makes the data encrypted with it unreadable. Back up keys separately from the database.

</details>

## 🏗️ Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Django 5.2, Django REST Framework, gunicorn, WhiteNoise |
| Frontend | Server-rendered Django templates + plain JavaScript (no build step) |
| Database | SQLite by default; PostgreSQL via `DATABASE_URL` |
| Encryption | `cryptography` (Fernet), WebCrypto (AES-256-GCM, PBKDF2) for the end-to-end vault, Paillier homomorphic encryption, Pedersen commitments + Fiat–Shamir zero-knowledge proofs |
| App | Installable PWA: web manifest + service worker with offline pages |
| AI & data | scikit-learn (TF-IDF), pandas, RapidOCR (ONNX), pypdf, optional OpenAI |
| CI | GitHub Actions: ruff lint, tests with coverage on SQLite and PostgreSQL, Docker build + smoke test, Django's production checks; Dependabot updates; CodeQL (once the repo is public) |

<details>
<summary><b>All modules: pages and API endpoints</b></summary>

| Module | Page | API | What it does |
| --- | --- | --- | --- |
| Users | `/register/`, `/login/`, `/profile/` | `/api/users/` | Expiring token auth, rate-limited login; profile (state, city, stage, language) personalises other modules; password change, **data export**, **account deletion** |
| Business validation | `/business/validation/` | `/api/business/` | Financial estimate, strengths/risks, census market indicators, matching schemes, optional AI advice; optional 🔒 Confidential mode |
| Schemes | `/schemes/` | `/api/schemes/`, `/api/schemes/alerts/` | 25 curated central/state schemes; rule + TF-IDF recommender with reasons; status flags; alerts for new matches and deadlines |
| Funding | `/funding/` | `/api/funding/` | EMI + amortisation, affordability, PMEGP subsidy, loan routes |
| Private check (HE) | `/funding/` | `/api/privacy/financial-check/` | Paillier homomorphic loan-affordability check; server never sees the figures |
| Market | `/market/` | `/api/market/` | District demand-potential index per business category from Census 2011; state women-MSME ecosystem |
| Documents | `/documents/` | `/api/documents/`, `/api/documents/digilocker/` | OCR (RapidOCR / pypdf), PAN/Aadhaar/GSTIN/Udyam/IFSC validation, encrypted storage, masked fields, DigiLocker confirmation |
| Idea Vault (ZKP) | `/vault/`, `/vault/verify/` | `/api/ideas/`, `/api/ideas/key/` | End-to-end encrypted ideas (browser), Pedersen commitments, zero-knowledge ownership proofs, public verifier |
| Assistant | `/assistant/` | `/api/assistant/chat/` | 7 languages, text or voice (Web Speech API); knowledge-base answers, optional OpenAI |
| Safety | `/safety/` (no login needed) | `/api/safety/resources/` | Helplines, reporting portals, safety guides; available offline in the installed app |

The frontend is in `empowerher/backend/frontend/` and the backend apps are in `empowerher/backend/apps/`. See [empowerher/backend/README.md](empowerher/backend/README.md) for the code layout.

</details>

## 🔒 How your data is protected

There is no automatic "sensitive or not" detection. **The user decides**, by choosing a module or by ticking **Confidential** on the Business Validation form.

| Data | How it is stored |
| --- | --- |
| Business idea, **normal** | Plain text, so the server can build the report (and send it to the AI if enabled) |
| Business idea, **🔒 Confidential** | Description and target customers **encrypted** (Fernet); never sent to the AI |
| Idea Vault idea | **End-to-end encrypted in the browser** (AES-256-GCM, key from your vault passphrase); the server stores only ciphertext and commitments |
| Uploaded documents and OCR text | **Encrypted** (Fernet, separate key) |
| ID numbers read from documents | **Masked**: PAN `ABXXX1234F`, Aadhaar `XXXX XXXX 1234` |
| Income and EMIs in the private check | **Never stored**; the server only sees Paillier ciphertexts |
| Password | **Hashed** (PBKDF2-SHA256 with salt) |
| Login token | In an **HttpOnly cookie** that page scripts can't read, with CSRF protection; **expires after 7 days**, replaced at every login and password change |
| Profile phone number and city | **Encrypted** (Fernet) |
| Profile name, state, stage, language | Plain text, used to personalise results |

**Rule of thumb:** use **normal validation** for ideas you're happy to store readable, **🔒 Confidential** when the description reveals the idea, and the **Idea Vault** for an idea that must stay fully secret or that you may need to prove is yours later.

> [!IMPORTANT]
> The Idea Vault passphrase never leaves your device. **If you forget it, vault ideas cannot be recovered**, by you or by EmpowerHer.

<details>
<summary><b>End-to-end encrypted Idea Vault</b> (how it works)</summary>

Code: `frontend/static/js/vault-crypto.js` (browser) and `apps/idea_vault/` (server).

1. **Passphrase → key, on your device.** The first time, you choose a vault passphrase. The browser derives an AES-256-GCM key from it with PBKDF2-SHA256 (600,000 rounds, random per-user salt). The key is created *non-extractable* and lives only in memory while the page is open.
2. **The server keeps only public settings:** the salt, the round count and a small encrypted "key check" value, which lets the browser tell a wrong passphrase from a right one.
3. **Registering an idea:** the browser makes a random 32-byte witness, computes the Pedersen commitment `C = g^m · h^r mod p`, encrypts `{idea, witness}` with AES-GCM, and uploads only the ciphertext and `C`. The server checks that `C` is a valid group element but cannot read anything.
4. **Proving ownership:** the browser decrypts, builds the Fiat–Shamir proof (version 2, hashed with SHA-256) and shows it to you. The server's public verifier accepts it like any other proof.
5. **Older ideas** registered before this change stay server-encrypted (Fernet) and keep working, marked "server-encrypted (older)".

The JavaScript and Python implementations are checked against each other: the same idea and witness give the same commitment, and browser-made proofs verify on the server.

</details>

<details>
<summary><b>Fernet encryption at rest</b> (confidential ideas, documents, profile, older vault ideas)</summary>

[Fernet](https://cryptography.io/en/latest/fernet/) from the `cryptography` library is authenticated symmetric encryption:
- AES-128 in CBC mode with a random 128-bit IV for every message;
- an HMAC-SHA256 tag, so any change to the ciphertext is detected and decryption fails;
- a timestamp.

Keys:
- **Two separate keys**, both read from `backend/.env` (see `apps/idea_vault/encryption.py` and `config/crypto.py`). A leak of one does not expose the other kind of data.
  - `IDEA_VAULT_ENCRYPTION_KEY` protects ideas: confidential business-validation ideas and older (server-encrypted) vault ideas.
  - `DOCUMENT_ENCRYPTION_KEY` protects personal data: uploaded documents and the profile's phone number and city.
- **Keys are never stored in the database and never generated automatically.** A new key would make existing data unreadable, so the server refuses to start encryption without one.
- **Even the admin panel cannot show ciphertext:** the encrypted fields are excluded there.

</details>

<details>
<summary><b>Idea Vault (older, server-encrypted ideas): what happens on registration</b></summary>

Code: `apps/idea_vault/views.py`

1. **Encrypt.** The idea text is encrypted with the vault key, and only the ciphertext is saved (`encrypted_idea`). The title stays plain so it can be listed.
2. **Create a witness.** A random 32-byte **witness secret** is generated.
3. **Store two commitments.** Both are fingerprints of the idea that reveal nothing about it:
   - `commitment` = SHA-256(`"EmpowerHer-Idea-Commitment-v1:"` + witness + idea);
   - `pedersen_commitment` = `g^m · h^r mod p`, where `m` = hash(idea) and `r` is derived from the witness. This one supports zero-knowledge proofs.
4. **Hand over the witness once.** It is returned to the owner a single time and **never stored**.
5. **Viewing.** Only the owner's account can request decryption (`GET /api/ideas/<id>/`). The list endpoint never returns ciphertext or plaintext.
6. **Proving ownership.** The owner submits the witness. The server checks it against the stored commitment, then produces a zero-knowledge proof.

</details>

<details>
<summary><b>Confidential business validation: what happens on submit</b></summary>

Code: `apps/business/views.py`

1. **Build the report in memory.** The report is calculated from the plain text: completeness, finances, market data and TF-IDF scheme matching.
2. **Keep the text out of the report.** Target customers in the report are replaced with "Confidential (encrypted)". The description is never copied into the report.
3. **Seal the free text.** `BusinessIdea.seal_confidential_fields()` encrypts the description and target customers together as one Fernet token (`encrypted_details`) and blanks the plain columns. Only then is the row saved.
4. **AI sees only the safe fields.** If OpenAI is configured, it receives the name, category, location, figures, market indicators and scheme names, but **never** the description or target customers.
5. **Owner access.** `BusinessIdea.confidential_details()` can decrypt the text for its owner.

Tests in `apps/business/tests.py` check the database row, the saved report and the exact OpenAI request (mocked).

</details>

<details>
<summary><b>Documents: what happens on upload</b></summary>

Code: `apps/documents/views.py`

1. **Check the file.** Its size (≤ 8 MB) and its real file signature are checked, not just the extension.
2. **OCR in memory.** Text is extracted in memory, and the ID numbers are validated and masked.
3. **Encrypt and save.** The original file and the full OCR text are encrypted with the document key, and only the ciphertext is saved. Masked fields and check results are saved in plain form.
4. **Download.** Decryption happens only when the owner downloads the file. The response is marked `no-store`.

</details>

<details>
<summary><b>Homomorphic encryption (Paillier)</b></summary>

- **Server:** `apps/privacy/paillier.py`. **Browser:** `frontend/static/js/paillier.js`.
- The browser generates a 2048-bit key pair, encrypts income, expenses and EMIs, and sends only the public key and ciphertexts.
- The server computes `Enc(surplus)`, `Enc(12 × surplus)`, `Enc(EMI headroom)` and `Enc(total EMI)` using homomorphic addition and scalar multiplication.
- Only the browser can decrypt the results. Nothing is stored.

</details>

<details>
<summary><b>Zero-knowledge proof of idea ownership</b></summary>

- **Code:** `apps/idea_vault/zkp.py`.
- On registration, the server stores a Pedersen commitment `C = g^m · h^r mod p`:
  - `m` is a hash of the idea;
  - `r` is derived from a witness secret given only to the owner;
  - the group is the RFC 3526 2048-bit safe-prime group.
- The owner can later create a Fiat–Shamir Okamoto proof of knowledge of `(m, r)`, bound to a context string (who the proof is for).
- Anyone can verify the proof at `/vault/verify/`. They learn that the prover registered the idea at the time shown and knows it, and nothing about its contents.

</details>

<details>
<summary><b>Users' control over their data</b></summary>

From the **Profile** page, users can:
- **Download all their data** as JSON (`GET /api/users/export/`). Confidential and Idea Vault ideas are decrypted for the owner. Witness secrets are never stored, so they are not included.
- **Permanently delete their account** after confirming their password (`POST /api/users/delete-account/`). This removes the profile, assessments, vault entries and documents.
- **Change their password** (`POST /api/users/change-password/`), which logs out other sessions.

From the **Business Validation** history, users can view their own confidential details (decrypted) and delete individual assessments (`/api/business/<id>/`).

</details>

<details>
<summary><b>Login protection and rate limits</b></summary>

- **The website never sees the token.** Login puts it in an `HttpOnly`, `SameSite=Lax` cookie (`Secure` in production), so even an injected script can't steal it. Requests authenticated by the cookie must carry Django's CSRF token. Other API clients can still send `Authorization: Token …`.
- **Tokens expire** after `DJANGO_TOKEN_TTL_HOURS` (default 7 days) and are replaced at every login.
- **Rate limits:**
  - login, registration, password change and account deletion: `DJANGO_AUTH_RATE` per IP (default 10/minute);
  - public proof verification: 60/minute;
  - AI assistant and idea validation: `DJANGO_AI_RATE` per user (default 20/minute);
  - document uploads: `DJANGO_UPLOAD_RATE` per user (default 10/minute);
  - every endpoint: 120/minute per visitor IP and 600/minute per logged-in user.
- **Shared counters in production:** rate-limit counters use a file-based cache, so they apply across all gunicorn workers.

</details>

<details>
<summary><b>What is <i>not</i> protected yet</b></summary>

- **Normal business-validation ideas are plain text.** They are sent to OpenAI when an API key is configured. Tick **Confidential** to avoid both.
- **Some fields of confidential ideas stay readable.** The business name, category, location and figures are stored readable, because the report needs them.
- **Name, state, business stage and language are plain text** (phone number and city are encrypted).
- **The server can decrypt documents, confidential validation ideas and older vault ideas**, because it holds the Fernet keys. The protection is against database leaks, not against the server operator. New Idea Vault entries are end-to-end encrypted and safe even from the operator.
- **Login tokens are stored plainly in the database** (scripts in the browser can't read them, but someone with database access could use a valid one until it expires).
- **The SQLite file itself is not encrypted.** Use disk encryption, or PostgreSQL with encryption at rest, in production.

</details>

## 📚 Datasets

All in `empowerher/backend/datasets/`:

| File | Source |
| --- | --- |
| `raw/census.csv` | Census of India 2011, district tables (640 districts), via [nishusharma1608/India-Census-2011-Analysis](https://github.com/nishusharma1608/India-Census-2011-Analysis) |
| `raw/pib_women_msme_2024.pdf` | Ministry of MSME annexures (PIB, Feb 2024): women-owned MSMEs on Udyam/UAP, CGTMSE guarantees for women, PMEGP women beneficiaries, by state |
| `processed/districts.csv`, `processed/states.csv` | Built from the raw files by `python datasets/build_datasets.py`. The 2011 Telangana districts are mapped out of Andhra Pradesh |
| `curated/schemes.json` | 25 central and state schemes with eligibility, limits and official links |
| `curated/loan_products.json` | Loan routes with indicative interest ranges for EMI planning |
| `curated/safety_resources.json` | National helplines, reporting portals and safety guides |

## ⚠️ Limitations

- **Market data is old.** Census indicators are from 2011, the latest district-level census, and districts created since then appear under their parent district. The demand index ranks districts against each other; it does not forecast sales.
- **Scheme data can go stale.** Scheme limits, rates and eligibility change. Each scheme links to its official source, and the dataset records its review date. Re-check before relying on it.
- **Document checks are format checks** unless DigiLocker is switched on. DigiLocker confirmation needs EmpowerHer to be registered as a DigiLocker partner (API Setu); until then the feature stays off. It is tested against a simulated DigiLocker, not the real service.
- **Some schemes' status is uncertain.** Stand-Up India, PMEGP, PMFME and the Startup India Seed Fund had ended or were awaiting renewal when checked (13 Nov 2026); they are flagged "check status" with sources.
- **Privacy has limits.** See "What is not protected yet" above.
- **Not deployed yet.** The production configuration is ready, passes `check --deploy`, and runs in Docker with PostgreSQL, but it has not been run on a public server.
- **Only the assistant is multilingual.** The rest of the interface is in English.

## 📖 Documentation

| Document | What's in it |
| --- | --- |
| [EXPLAIN.md](EXPLAIN.md) | How the whole project works, and why it is secure |
| [SETUP.md](SETUP.md) | Installing, running, troubleshooting and deploying |
| [empowerher/backend/README.md](empowerher/backend/README.md) | Code layout |
| [report/](report/) | Final project report, results chapter, screenshots and charts |

## 📄 Licence

[MIT](LICENSE) © 2026 Vishwa K

<div align="center">
<sub>Made with 💜 for women entrepreneurs.</sub>
</div>
