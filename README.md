# EmpowerHer

[![Tests](https://github.com/vishwa-10147/project_p/actions/workflows/tests.yml/badge.svg)](https://github.com/vishwa-10147/project_p/actions/workflows/tests.yml)

**A privacy-preserving AI framework for women entrepreneurship.**

New here? Read [EXPLAIN.md](EXPLAIN.md) for how the project works and why it is secure, [SETUP.md](SETUP.md) to run it, and [empowerher/backend/README.md](empowerher/backend/README.md) for the code layout. The frontend is in `empowerher/backend/frontend/` (Django templates + JavaScript, no React); the backend is in `empowerher/backend/apps/`.
Django + Django REST Framework backend with server-rendered pages.

## Quick start

**See [SETUP.md](SETUP.md).** One command sets up and runs everything:

```bash
./setup.sh          # macOS / Linux
setup.bat           # Windows
```

The script creates the virtual environment, installs packages, generates encryption keys in `empowerher/backend/.env`, prepares the database and datasets, creates a demo account, and opens http://localhost:8000.

Environment variables in `empowerher/backend/.env`:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key |
| `IDEA_VAULT_ENCRYPTION_KEY` | Encrypts Idea Vault ideas and confidential business ideas (Fernet) |
| `DOCUMENT_ENCRYPTION_KEY` | Encrypts uploaded documents and their OCR text (Fernet) |
| `OPENAI_API_KEY` | Optional. Enables AI recommendations and AI assistant answers |
| `OPENAI_MODEL` | Optional, default `gpt-4.1-mini` |
| `DJANGO_TOKEN_TTL_HOURS` | Optional, login session lifetime (default 168 = 7 days) |
| `DJANGO_AUTH_RATE` | Optional, login/registration rate limit (default `10/minute`) |
| `DJANGO_AI_RATE` | Optional, AI assistant and idea validation limit per user (default `20/minute`) |
| `DJANGO_UPLOAD_RATE` | Optional, document upload (OCR) limit per user (default `10/minute`) |
| `DATABASE_URL` | Optional, e.g. `postgres://user:pass@host:5432/empowerher`; SQLite when unset |
| `DJANGO_DEBUG` | `True` for local development (setup writes this). **Off by default** |

For production variables (`DJANGO_DEBUG=False`, domain, HTTPS), see `empowerher/backend/.env.production.example` and the production section of [SETUP.md](SETUP.md); `./run_production.sh` starts gunicorn.

Losing an encryption key makes the data encrypted with it unreadable. Back keys up separately from the database.

Useful commands (run from `empowerher/backend` with the virtual environment's Python):

| Command | Purpose |
| --- | --- |
| `python manage.py test` | Run the 74 automated tests (also run by GitHub Actions on every push) |
| `python manage.py seed_demo` | Create or reset the demo account |
| `python manage.py run_benchmarks` | Measure performance (results in `report/results/benchmarks.json`) |
| `python datasets/build_datasets.py` | Rebuild the processed datasets from the raw downloads |

## Modules

| Module | Page | API | What it does |
| --- | --- | --- | --- |
| Users | `/register/`, `/login/`, `/profile/` | `/api/users/` | Expiring token auth, rate-limited login; profile (state, city, stage, language) personalises other modules; password change, **data export**, **account deletion** |
| Business validation | `/business/validation/` | `/api/business/` | Financial estimate, strengths/risks, census market indicators, matching schemes, optional AI advice; optional 🔒 Confidential mode |
| Schemes | `/schemes/` | `/api/schemes/` | 25 curated central/state schemes; rule + TF-IDF recommender with reasons |
| Funding | `/funding/` | `/api/funding/` | EMI + amortisation, affordability, PMEGP subsidy, loan routes |
| Private check (HE) | `/funding/` | `/api/privacy/financial-check/` | Paillier homomorphic loan-affordability check; server never sees the figures |
| Market | `/market/` | `/api/market/` | District demand-potential index per business category from Census 2011; state women-MSME ecosystem |
| Documents | `/documents/` | `/api/documents/` | OCR (RapidOCR / pypdf), PAN/Aadhaar/GSTIN/Udyam/IFSC validation, encrypted storage, masked fields |
| Idea Vault (ZKP) | `/vault/`, `/vault/verify/` | `/api/ideas/` | Encrypted ideas, Pedersen commitments, zero-knowledge ownership proofs, public verifier |
| Assistant | `/assistant/` | `/api/assistant/chat/` | English/Telugu/Hindi, text or voice (Web Speech API); knowledge-base answers, optional OpenAI |
| Safety | `/safety/` | `/api/safety/resources/` | Helplines, reporting portals, safety guides |

## Data protection

### Which data is encrypted, and how the split is decided

There is no automatic "sensitive or not" detection. **The user decides**, either by choosing a module or by ticking the **Confidential** option on the Business Validation form. Each module is designed for one kind of data:

| Data | Where it is entered | How it is stored | Why |
| --- | --- | --- | --- |
| Business idea for validation, **normal** | Business Idea Validation | **Plain text** in `business_businessidea` | The server needs readable data to calculate the report, match schemes and market data, show history and (if enabled) send it to the AI |
| Business idea for validation, **🔒 Confidential ticked** | Business Idea Validation | Description and target customers **encrypted** (Fernet, in `encrypted_details`); name, category, location and figures stay plain | The figures, place and category are enough for the report, schemes and market data; the free text is the part that reveals the idea |
| Confidential idea | Idea Vault | **Encrypted** (Fernet) + commitments | Meant for ideas the user wants to protect; readable only through the owner's account |
| Uploaded document file and its full OCR text | Documents | **Encrypted** (Fernet, separate key) | Identity and financial documents |
| Fields read from documents | Documents | Plain, but **masked**: PAN `ABXXX1234F`, Aadhaar `XXXX XXXX 1234` | Lets the page show what was found without keeping full ID numbers |
| Income, expenses, EMIs in the private check | Funding → Private check | **Never stored**; the server only sees Paillier ciphertexts | Computed under homomorphic encryption |
| Password | Register / Login | **Hashed** (Django PBKDF2-SHA256 with salt), not encrypted | Cannot be reversed |
| Login token | Login | Random token; **expires after 7 days**; replaced at every login and password change | Limits the damage of a stolen token |
| Profile (name, phone, city, state, stage, language) | Register / Profile | Plain text | Used to personalise schemes, market and assistant |

**Rule of thumb for users:**
- **Normal validation:** use it for ideas you are happy to have stored readable.
- **🔒 Confidential validation:** use it when the description or target customers reveal your idea. You still get the full report, but that text is encrypted and is not sent to the AI.
- **Idea Vault:** use it for an idea that must stay fully secret, or that you want to prove is yours later (zero-knowledge proof). The Vault encrypts everything except the title.

### Fernet encryption at rest (Idea Vault, confidential ideas, Documents)

[Fernet](https://cryptography.io/en/latest/fernet/) from the `cryptography` library is authenticated symmetric encryption:
- AES-128 in CBC mode with a random 128-bit IV for every message;
- an HMAC-SHA256 tag, so any change to the ciphertext is detected and decryption fails;
- a timestamp.

Keys:
- **Two separate keys**, both read from `backend/.env` (see `apps/idea_vault/encryption.py` and `config/crypto.py`). A leak of one does not expose the other kind of data.
  - `IDEA_VAULT_ENCRYPTION_KEY` protects ideas: the Idea Vault and confidential business-validation ideas.
  - `DOCUMENT_ENCRYPTION_KEY` protects uploaded documents.
- **Keys are never stored in the database and never generated automatically.** A new key would make existing data unreadable, so the server refuses to start encryption without one.
- **Even the admin panel cannot show ciphertext:** the encrypted fields are excluded there.

#### Idea Vault: what happens when an idea is registered (`apps/idea_vault/views.py`)

1. **Encrypt.** The idea text is encrypted with the vault key, and only the ciphertext is saved (`encrypted_idea`). The title stays plain so it can be listed.
2. **Create a witness.** A random 32-byte **witness secret** is generated.
3. **Store two commitments.** Both are fingerprints of the idea that reveal nothing about it:
   - `commitment` = SHA-256(`"EmpowerHer-Idea-Commitment-v1:"` + witness + idea);
   - `pedersen_commitment` = `g^m · h^r mod p`, where `m` = hash(idea) and `r` is derived from the witness. This one supports zero-knowledge proofs.
4. **Hand over the witness once.** It is returned to the owner a single time and **never stored**.
5. **Viewing.** Only the owner's account can request decryption (`GET /api/ideas/<id>/`). The list endpoint never returns ciphertext or plaintext.
6. **Proving ownership.** The owner submits the witness. The server checks it against the stored commitment, then produces a zero-knowledge proof (described below).

#### Confidential business validation: what happens on submit (`apps/business/views.py`)

1. **Build the report in memory.** The idea is built in memory with the plain text, and the report is calculated: completeness, finances, market data and TF-IDF scheme matching.
2. **Keep the text out of the report.** Target customers in the report are replaced with "Confidential (encrypted)". The description is never copied into the report.
3. **Seal the free text.** `BusinessIdea.seal_confidential_fields()` encrypts the description and target customers together as one Fernet token (`encrypted_details`) and blanks the plain columns. Only then is the row saved.
4. **AI sees only the safe fields.** If OpenAI is configured, it receives the name, category, location, figures, market indicators and scheme names, but **never** the description or target customers.
5. **Owner access.** `BusinessIdea.confidential_details()` can decrypt the text for its owner.

Tests in `apps/business/tests.py` check the database row, the saved report and the exact OpenAI request (mocked).

#### Documents: what happens on upload (`apps/documents/views.py`)

1. **Check the file.** Its size (≤ 8 MB) and its real file signature are checked, not just the extension.
2. **OCR in memory.** Text is extracted in memory, and the ID numbers are validated and masked.
3. **Encrypt and save.** The original file and the full OCR text are encrypted with the document key, and only the ciphertext is saved. Masked fields and check results are saved in plain form.
4. **Download.** Decryption happens only when the owner downloads the file. The response is marked `no-store`.

### Homomorphic encryption (Paillier)
- **Server:** `apps/privacy/paillier.py`. **Browser:** `frontend/static/js/paillier.js`.
- The browser generates a 2048-bit key pair, encrypts income, expenses and EMIs, and sends only the public key and ciphertexts.
- The server computes `Enc(surplus)`, `Enc(12 × surplus)`, `Enc(EMI headroom)` and `Enc(total EMI)` using homomorphic addition and scalar multiplication.
- Only the browser can decrypt the results. Nothing is stored.

### Zero-knowledge proof of idea ownership
- **Code:** `apps/idea_vault/zkp.py`.
- On registration, the server stores a Pedersen commitment `C = g^m · h^r mod p`:
  - `m` is a hash of the idea;
  - `r` is derived from a witness secret given only to the owner;
  - the group is the RFC 3526 2048-bit safe-prime group.
- The owner can later create a Fiat–Shamir Okamoto proof of knowledge of `(m, r)`, bound to a context string (who the proof is for).
- Anyone can verify the proof at `/vault/verify/`. They learn that the prover registered the idea at the time shown and knows it, and nothing about its contents.

### Users' control over their data

From the **Profile** page, users can:
- **Download all their data** as JSON (`GET /api/users/export/`). Confidential and Idea Vault ideas are decrypted for the owner. Witness secrets are never stored, so they are not included.
- **Permanently delete their account** after confirming their password (`POST /api/users/delete-account/`). This removes the profile, assessments, vault entries and documents.
- **Change their password** (`POST /api/users/change-password/`), which logs out other sessions.

From the **Business Validation** history, users can view their own confidential details (decrypted) and delete individual assessments (`/api/business/<id>/`).

### Login protection
- **Tokens expire** after `DJANGO_TOKEN_TTL_HOURS` (default 7 days) and are replaced at every login.
- **Rate limits:** login, registration, password change and account deletion are limited per IP (`DJANGO_AUTH_RATE`, default 10/minute). Public proof verification is limited to 60/minute. The AI assistant and idea validation are limited per user (`DJANGO_AI_RATE`, default 20/minute), document uploads too (`DJANGO_UPLOAD_RATE`, default 10/minute), and every endpoint has an overall limit (120/minute per visitor IP, 600/minute per logged-in user).
- **Shared counters in production:** rate-limit counters use a file-based cache, so they apply across all gunicorn workers.

### What is *not* protected yet
- **Normal business-validation ideas are plain text.** They are sent to OpenAI when an API key is configured. Tick **Confidential** to avoid both.
- **Some fields of confidential ideas stay readable.** The business name, category, location and figures are stored readable, because the report needs them.
- **Profile details are plain text.**
- **The server can decrypt vault ideas and documents**, because it holds the Fernet keys. The protection is against database leaks and against verifiers (investors, mentors), not against the server operator. True end-to-end protection would need the encryption to happen in the browser.
- **Login tokens are stored plainly**, in the database and in the browser's `localStorage`. They expire, but anyone who copies a valid token can use it until then.
- **The SQLite file itself is not encrypted.** Use disk encryption, or PostgreSQL with encryption at rest, in production.

## Datasets (`empowerher/backend/datasets/`)

| File | Source |
| --- | --- |
| `raw/census.csv` | Census of India 2011, district tables (640 districts), via [nishusharma1608/India-Census-2011-Analysis](https://github.com/nishusharma1608/India-Census-2011-Analysis) |
| `raw/pib_women_msme_2024.pdf` | Ministry of MSME annexures (PIB, Feb 2024): women-owned MSMEs on Udyam/UAP, CGTMSE guarantees for women, PMEGP women beneficiaries, by state |
| `processed/districts.csv`, `processed/states.csv` | Built from the raw files by `python datasets/build_datasets.py`. The 2011 Telangana districts are mapped out of Andhra Pradesh |
| `curated/schemes.json` | 25 central and state schemes with eligibility, limits and official links |
| `curated/loan_products.json` | Loan routes with indicative interest ranges for EMI planning |
| `curated/safety_resources.json` | National helplines, reporting portals and safety guides |

## Limitations
- **Market data is old.** Census indicators are from 2011, the latest district-level census, and districts created since then appear under their parent district. The demand index ranks districts against each other; it does not forecast sales.
- **Scheme data can go stale.** Scheme limits, rates and eligibility change. Each scheme links to its official source, and the dataset records its review date. Re-check before relying on it.
- **Document checks are format checks.** They confirm number formats and checksums only, not authenticity with the issuing authority (that needs DigiLocker or an authorised API).
- **Privacy has limits.** See "What is not protected yet" above.
- **Not deployed yet.** The production configuration is ready and passes `check --deploy`, but it has not been run on a public server. It uses SQLite by default; set `DATABASE_URL` to use PostgreSQL for many concurrent users.

## Licence

MIT. See [LICENSE](LICENSE).
