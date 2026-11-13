# EmpowerHer: How It Works and Why It Is Secure

This document explains EmpowerHer for students, reviewers and examiners: what the project does, how it is built, how data moves through it, and how each kind of data is protected. For setup, see [SETUP.md](SETUP.md); for a feature reference, see [README.md](README.md).

---

## 1. What EmpowerHer is

EmpowerHer is a web application for women entrepreneurs in India. It brings together, in one place, the help a woman starting or growing a business usually has to find across many websites and offices:

| Need | What EmpowerHer gives |
| --- | --- |
| "Is my idea viable?" | **Business idea validation:** revenue, profit, margin, strengths, risks, suggestions, local demand data and matching schemes |
| "What government help can I get?" | **Scheme recommendations:** 25 central and state schemes, ranked for her state, stage, category, amount and social group, each with reasons and an official link |
| "Can I afford a loan?" | **Funding tools:** EMI calculator, affordability check, PMEGP subsidy split, loan routes |
| "Is there demand where I live?" | **Market analysis:** a 0–100 demand index for her district and business category, from Census 2011 data on all 640 districts, plus state-wise data on women-owned businesses |
| "Are my documents in order?" | **Document verification:** OCR reads PAN, Aadhaar, GST and Udyam documents and checks the numbers |
| "How do I protect my idea?" | **Idea Vault:** stores the idea encrypted and lets her prove she owns it **without revealing it** (zero-knowledge proof) |
| "I prefer my own language" | **Assistant:** answers in English, Telugu, Hindi, Tamil, Kannada, Marathi or Bengali, typed or spoken |
| "Am I safe?" | **Safety:** emergency numbers, reporting portals, safety guides |

What makes the project different from an ordinary information portal is **privacy**. Sensitive figures can be processed while still encrypted (homomorphic encryption), ownership of an idea can be proven without disclosing it (zero-knowledge proof), and confidential text is encrypted at rest and kept away from external AI services.

---

## 2. Architecture

```
 ┌──────────────────────────── Browser ────────────────────────────┐
 │  HTML pages (Django templates) + JavaScript                     │
 │   - calls the REST API with a login token                       │
 │   - Paillier key generation / encryption / decryption (paillier.js)
 │   - voice input/output (Web Speech API)                         │
 └───────────────────────────────┬─────────────────────────────────┘
                                 │ HTTPS (production)
 ┌───────────────────────────────▼─────────────────────────────────┐
 │  Django 5 + Django REST Framework  (gunicorn in production)     │
 │                                                                 │
 │  users      business    schemes    funding    market            │
 │  documents  idea_vault  privacy    assistant  safety            │
 │                                                                 │
 │  config/: settings, expiring-token auth, Fernet helpers,        │
 │           dataset loader                                        │
 └──────┬──────────────────────┬───────────────────────┬──────────┘
        │                      │                       │
  ┌─────▼──────┐   ┌───────────▼──────────┐  ┌─────────▼─────────┐
  │  SQLite    │   │  datasets/ (read-only)│  │ OpenAI (optional) │
  │  database  │   │  Census, MSME, schemes│  │ only if key set,  │
  │            │   │  loans, safety        │  │ never confidential│
  └────────────┘   └──────────────────────┘  └───────────────────┘
```

- **One server.** The same Django server provides the pages (frontend) and the JSON API (backend). Each page loads, then fetches its data from the API with the user's login token.
- **Code layout.** The **backend** is in `empowerher/backend/apps/`, one folder per feature, each with `views.py` (API), `urls.py`, and logic modules such as `recommender.py`, `analysis.py`, `paillier.py`, `zkp.py` and `ocr.py`. The **frontend** (HTML pages and JavaScript) is in `empowerher/backend/frontend/`. Section 8 has the full map.
- **Data.** The database holds users and their records. Reference data (schemes, census and so on) is read from files in `datasets/` and never changed by users.
- **Size.** About 6,000 lines of Python in 11 apps, 18 page templates, and 127 automated tests with 85% code coverage (run automatically on GitHub for every push, on SQLite and PostgreSQL).

### Technology stack

| Layer | Technology |
| --- | --- |
| Language / framework | Python 3.11–3.13, Django 5.2, Django REST Framework |
| Frontend | Django templates, plain JavaScript, responsive CSS |
| Database | SQLite by default; PostgreSQL via `DATABASE_URL` (recommended for large deployments) |
| Encryption at rest | `cryptography` — Fernet (AES-128-CBC + HMAC-SHA256) |
| Homomorphic encryption | Paillier, own implementation in Python (server) and JavaScript (browser) |
| Zero-knowledge proof | Pedersen commitments + Okamoto/Schnorr proof, 2048-bit group (RFC 3526) |
| OCR | RapidOCR (PaddleOCR models on ONNX Runtime), pypdf |
| Recommendations | scikit-learn TF-IDF + rules |
| Data analysis | pandas, NumPy |
| AI (optional) | OpenAI Responses API |
| Production serving | gunicorn, WhiteNoise |

---

## 3. How each module works

### 3.1 Users and profile (`apps/users/`)
- **Registration** creates a Django user and an `EntrepreneurProfile` (phone, city, state, business stage, preferred language).
- **Login** checks the password and returns a random **token**. The browser stores it and sends it with every API request as `Authorization: Token …`.
- **Personalisation.** The profile's state, stage and language are used by the scheme recommender, the market page and the assistant.
- **Self-service.** Users can change their password, download all their data, or delete their account (Section 5.10).

### 3.2 Business idea validation (`apps/business/`)
1. **Input validation.** Required fields, length limits, categories, and numbers that must be finite and non-negative, with whole units for sales.
2. **Financial model:**
   - revenue = price × units;
   - profit = revenue − expenses;
   - margin = profit ÷ revenue;
   - plus a "completeness" score showing how fully the form was filled in. This is **not** a success probability.
3. **Rule-based strengths, risks and suggestions.**
4. **Market research** from the market module (3.5) for the idea's district and category.
5. **Top 3 schemes** from the recommender (3.3).
6. **Optional AI advice** (OpenAI) built only from the figures and the facts above. The AI is told never to invent schemes or statistics.
7. **🔒 Confidential option** (Section 5.4): the description and target customers are encrypted and never sent to the AI.

### 3.3 Scheme recommendation (`apps/schemes/recommender.py`)
For every scheme in `datasets/curated/schemes.json`:
1. **Hard rules exclude schemes that cannot apply:**
   - a state scheme for another state;
   - a scheme for a different business stage;
   - a scheme reserved for a group the user isn't in (SC/ST, OBC, minority, artisan, street vendor).
2. **Soft scoring adds points:**
   - state match +20 and category match +20;
   - women-specific scheme +10;
   - amount fits +10 and stage +10;
   - social-group match +15.
   - **Text similarity:** TF-IDF cosine similarity between the user's description and the scheme's text, worth up to +60.
3. **Results are sorted by score.** Each one lists its **reasons** (✓) and **cautions** (⚠), so the recommendation is explainable.

### 3.4 Funding (`apps/funding/calculator.py`)
- **EMI** = P·r·(1+r)ⁿ ÷ ((1+r)ⁿ − 1), where r is the monthly rate and n the number of months, with a year-by-year amortisation schedule.
- **Affordability:** lenders typically allow EMIs of up to about 50% of monthly surplus. The tool works out the affordable EMI and inverts the EMI formula to get the maximum loan.
- **PMEGP split for women:**
  - 5% own contribution;
  - subsidy of 25% (urban) or 35% (rural);
  - the rest as a bank loan.
- **Loan routes** for the amount come from `loan_products.json`.

### 3.5 Market demand (`apps/market/analysis.py`)
- **Data:**
  - **Census 2011:** 640 districts, 118 columns. The 10 Telangana districts are separated from the 2011 Andhra Pradesh data.
  - **Ministry of MSME (PIB, Feb 2024):** women-owned MSMEs, CGTMSE guarantees and PMEGP projects, by state.
- **Indicators per category.** Each business category uses census indicators that act as demand signals. For example, food uses population, urban share, working women, higher-income households and two-wheelers; technology uses internet, computers, graduates and urban share.
- **Scoring.** Each indicator becomes a **percentile across all 640 districts**. A weighted average gives the **demand potential index** (0–100), along with the district's rank in its state and plain-language insights.
- **Ecosystem.** The state's women-owned MSMEs per 1,000 women are compared with the national average, which signals both how strong the support ecosystem is and how much competition to expect.

### 3.6 Documents (`apps/documents/`)
1. **Upload checks:** the file must be under 8 MB, and its real file signature must match its type (PDF, JPEG, PNG or WebP).
2. **Text extraction:**
   - **PDF** text with pypdf;
   - **images** with RapidOCR, after correcting orientation and adding a margin;
   - **scanned PDFs** by running OCR on their embedded images.
3. **Document type detection** from keywords, which tolerate OCR dropping spaces.
4. **Number validation:**
   - **PAN:** format, plus the holder-type letter;
   - **Aadhaar:** 12 digits and the **Verhoeff checksum**;
   - **GSTIN:** 15 characters and its **base-36 check character**;
   - **Udyam:** format;
   - **IFSC:** format;
   - **name:** compared with the user's profile name.
5. **Status:** "Checks passed", "Needs review" or "Could not read document".
6. **Storage:** see Section 5.5. The file is encrypted and only masked numbers are kept.

### 3.7 Idea Vault (`apps/idea_vault/`)
- **Registering** an idea encrypts it **in the browser** with a key made from the owner's vault passphrase (end-to-end: the server stores only ciphertext) and creates a timestamped commitment. The witness secret is encrypted together with the idea, so the owner needs only her passphrase. Older ideas registered before end-to-end encryption are server-encrypted and use a one-time witness secret.
- **Proving ownership.** The owner can later create a **zero-knowledge proof of ownership** for a named recipient.
- **Verifying.** Anyone can check the proof at `/vault/verify/`. The proof shows the prover registered the idea at that time and knows it, without revealing the idea. Section 5.7 explains the mathematics.

### 3.8 Private affordability check (`apps/privacy/`)
The browser and server compute loan affordability **on encrypted numbers** using Paillier homomorphic encryption. Section 5.6 explains how.

### 3.9 Assistant (`apps/assistant/engine.py`)
1. **Detect the intent** (schemes, loan, EMI, safety, emergency, market, documents, privacy, validation, greeting) from keywords in English, Telugu, Hindi, Tamil, Kannada, Marathi and Bengali.
2. **Gather facts from EmpowerHer's own data:**
   - scheme recommendations for the user's profile;
   - loan routes;
   - helplines;
   - a calculated EMI, when the question includes an amount, rate and tenure ("5 lakh at 10% for 3 years").
3. **Answer:**
   - **Without an AI key:** answer templates in the chosen language.
   - **With a key:** the facts are given to the AI as its only source of truth.
   - **Emergencies** always get the fixed safety answer (call 112), never an AI answer.
4. **Voice:** speech recognition and speech output use the browser's Web Speech API (`en-IN`, `te-IN`, `hi-IN`).

### 3.10 Safety (`apps/safety/`)
- **Emergency:** a large "Call 112" button.
- **Helplines:** national numbers (112, 181, 1930, NCW), plus Telangana SHE Teams (via Dial 100 or the Hawk Eye app) for users in Telangana.
- **Reporting portals:** cybercrime.gov.in, SHe-Box, RBI Sachet and the RBI complaint system.
- **Guides:** digital payments, fake loan apps, online presence, meeting customers, POSH rights, protecting ideas.

---

## 4. A request from start to finish

Example: a logged-in user submits a **confidential** business idea.

```
Browser                                 Server (Django)
───────                                 ───────────────
POST /api/business/validate/  ───────►  1. Rate limits / security middleware
Authorization: Token 3f9a…               2. ExpiringTokenAuthentication:
JSON body (idea, figures,                   token exists? younger than 7 days?
 is_confidential: true)                  3. IsAuthenticated permission
                                         4. validate_business_data(): types, limits
                                         5. Build idea in memory; generate_report()
                                            (finances, census market data, schemes)
                                         6. seal_confidential_fields():
                                            description + target customers
                                            → Fernet ciphertext; plain columns blanked
                                         7. Save row + report (no secret text in it)
                                         8. AI call (if configured) WITHOUT the
                                            description/target customers
◄──────── 201 JSON report ─────────────  9. Return the report
Page renders it with textContent
(never as HTML)
```

---

## 5. Security in detail

Security is built in **layers**, so a failure in one layer is limited by the others.

### 5.1 Threat model: what we protect against

| Threat | Main defences |
| --- | --- |
| Someone steals the database file | Ideas, confidential text, documents and OCR text are encrypted; passwords are hashed; Aadhaar is never stored in full |
| A user tries to read another user's data | Every query is filtered by owner; other users' records return 404 |
| Someone guesses passwords | Strong-password rules, rate-limited login, PBKDF2 hashing |
| A stolen or old login token | Tokens expire (7 days), are replaced at each login and password change, and are deleted on logout |
| Network eavesdropping | HTTPS-only in production (redirect + HSTS + secure cookies) |
| Malicious input / XSS | Input validation; all user text inserted with `textContent`; Django auto-escaping; no `innerHTML` anywhere |
| Malicious file upload | Size limit, real file-signature check, files never served without decryption by the owner |
| An investor copies a shared idea | Zero-knowledge proof proves ownership without revealing the idea |
| A service needs financial figures | Homomorphic encryption: the server computes without seeing them |
| Confidential text leaking to third parties | Confidential mode keeps it out of the AI request entirely |
| Clickjacking, cross-site requests | `X-Frame-Options: DENY`; token auth in headers; CSRF middleware for session (admin) use; CORS restricted in production |
| Fake or replayed ownership proofs | Proofs are bound to a context string and checked against stored commitments |

### 5.2 Authentication: who you are
- **Passwords** are never stored. Django stores a **PBKDF2-SHA256 hash with a random salt** and a high iteration count, so a leaked hash cannot be reversed back to the password.
- **Password strength** is enforced by four validators: not similar to the username, a minimum length, not a common password, and not entirely numeric.
- **Login tokens** (`config/authentication.py`):
  - **Random:** each token is a random value tied to one user.
  - **Expiring:** valid for `DJANGO_TOKEN_TTL_HOURS` (default 168 hours = 7 days). An expired token is deleted and the user must log in again.
  - **Replaced:** every login and every password change issues a **new** token, so old copies stop working.
  - **Logout** deletes the token.
- **Rate limiting** (Django REST Framework throttling):
  - login, registration, password change and account deletion: 10 per minute per IP address;
  - public proof verification: 60 per minute;
  - AI assistant and idea validation: 20 per minute per user (they may call the OpenAI API);
  - document uploads: 10 per minute per user (OCR is CPU-heavy); listing documents is not limited;
  - every other endpoint: 120 per minute per visitor IP, 600 per minute per logged-in user.
  - In production the counters are stored in a shared file cache, so the limit holds across all server workers. This was tested: with 3 workers, request 11 onwards is blocked.

### 5.3 Authorisation: what you may access
- **Login required.** Every endpoint that touches personal data requires a logged-in user (`IsAuthenticated` by default).
- **Owner-only access.** Every lookup of a personal record includes the owner: `get_object_or_404(Model, pk=pk, owner=request.user)`. There are 13 such filters in the code.
- **No leaks about other users' records.** A user who asks for someone else's idea, document or assessment gets **404 Not Found**, not 403. The response doesn't even reveal that the record exists. Tests check this for ideas, documents and assessments.
- **Public endpoints carry no personal data.** Only the scheme catalogue, calculators, market data, safety resources and proof verification are public.

### 5.4 Classifying data: what gets encrypted

There is no automatic guessing. **The user chooses** by picking a module or ticking the Confidential box, and each choice has a clear storage rule:

| Data | Stored as |
| --- | --- |
| Normal business-validation idea | Plain text (needed for the report; can go to the AI if enabled) |
| 🔒 Confidential business idea | Description + target customers **encrypted**; name, category, location and figures plain (needed for the report) |
| Idea Vault idea | **Encrypted** (only the title is plain) + commitments |
| Uploaded document file and full OCR text | **Encrypted** (separate key) |
| ID numbers found on documents | Plain but **masked** (`ABXXX1234F`, `XXXX XXXX 1234`) |
| Financial figures in the private check | **Never stored**, and never seen unencrypted by the server |
| Password | **Hashed** (one-way) |
| Profile | Plain text |

### 5.5 Encryption at rest (Fernet)

[Fernet](https://cryptography.io/en/latest/fernet/) (`cryptography` library) is an **authenticated** encryption scheme:
- **AES-128 in CBC mode**, with a **fresh random IV** for every value, so the same idea encrypted twice gives different ciphertext;
- an **HMAC-SHA256** tag over the data, so if anyone modifies the ciphertext, decryption **fails** instead of returning altered data;
- a timestamp.

**Keys:**
- **Two separate keys** live in `empowerher/backend/.env`:
  - `IDEA_VAULT_ENCRYPTION_KEY` for ideas (Idea Vault and confidential business ideas);
  - `DOCUMENT_ENCRYPTION_KEY` for documents.

  A leak of one doesn't expose the other.
- **Keys are never stored in the database,** never committed to git, and never generated automatically at startup (that would make old data unreadable). The setup script creates them once.
- **Admins can't see ciphertext either:** encrypted fields are hidden from the Django admin panel.

**Masking ID numbers:**
- **Aadhaar:** the full number is **never stored**, in line with the UIDAI rule that only the last four digits may be displayed.
- **PAN:** stored partially masked.
- **The full text** read from a document exists only inside the encrypted OCR text.

### 5.6 Homomorphic encryption: computing on encrypted numbers (Paillier)

**The problem:** to check loan affordability, a server normally needs your income and expenses. With homomorphic encryption, it never sees them.

**Paillier encryption.**
- **Keys:**
  - the public key is n = p·q, the product of two random primes (2048-bit n);
  - the private key is λ = lcm(p−1, q−1), together with μ = λ⁻¹ mod n.
- **Encryption:** Enc(m) = (1 + m·n) · rⁿ mod n², with a fresh random r each time, so encryptions are randomised.
- **Homomorphic properties:**
  - Enc(a) × Enc(b) mod n² = **Enc(a + b)**;
  - Enc(a)ᵏ mod n² = **Enc(k · a)**.

**Steps in EmpowerHer** (`frontend/static/js/paillier.js`, `apps/privacy/paillier.py`, `apps/privacy/views.py`):

1. **The browser generates the key pair.** The private key never leaves the page.
2. **The browser encrypts** income, expenses and existing EMIs, and sends only **n and the ciphertexts**. These are 4096-bit numbers that reveal nothing.
3. **The server computes on the ciphertexts:**
   - Enc(surplus) = Enc(income) · Enc(expenses)⁻¹;
   - Enc(yearly surplus) = Enc(surplus)¹²;
   - Enc(100 × EMI headroom) = Enc(income)^f · Enc(expenses)^−f · Enc(existing)^−100 · Enc(−100 · proposed), where f is the allowed percentage (50).
4. **The browser decrypts the results.** Example: income 60,000, expenses 35,000, existing EMIs 2,000 and a proposed EMI of 9,000 decrypt to a surplus of 25,000 and a headroom of 1,500. These match the plain calculation exactly.

**Safeguards and limits:**
- The server **stores nothing** from this check.
- It rejects keys outside 1024–4096 bits and invalid ciphertexts.
- The proposed EMI is sent in plain form on purpose: it is the loan offer, not private data.

### 5.7 Zero-knowledge proof of idea ownership

**The problem:** an entrepreneur wants to show an investor "I had this idea, registered on this date", without handing over the idea.

**The setup** (`apps/idea_vault/zkp.py`):
- **Group:** the 2048-bit safe prime p from RFC 3526, where q = (p−1)/2 is also prime. The proof works in the subgroup of order q, with generator g = 4 and a second generator h derived by hashing, so that nobody knows log_g(h).
- **Registration:** the server stores a **Pedersen commitment** C = gᵐ · hʳ mod p.
  - m is a hash of the idea.
  - r comes from the **witness secret**, which is given to the owner once and **never stored**.
- **Properties of C:**
  - **Hiding:** it reveals nothing about the idea.
  - **Binding:** nobody can later claim it belongs to a different idea.

**The proof** is an Okamoto (Schnorr-style) proof of knowledge of (m, r), made non-interactive with the Fiat–Shamir method:
```
pick random a, b
T  = gᵃ · hᵇ mod p
c  = Hash(C, T, context) mod q        ← context = who the proof is for
z₁ = a + c·m  mod q
z₂ = b + c·r  mod q
proof = (C, T, z₁, z₂, context)
```

**Verification.** The verifier checks gᶻ¹ · hᶻ² ≡ T · Cᶜ (mod p). EmpowerHer also checks that C is a **registered** commitment and shows when it was registered.

**Guarantees:**
- **Zero-knowledge:** the verifier learns nothing about m or r.
- **Sound:** a valid proof cannot be made without knowing m and r.
- **Bound to the context:** a proof made for "Investor A" fails if presented as "Investor B".
- **Tamper-evident:** changing any number makes verification fail.

**Supporting checks:**
- The server only produces a proof after checking the witness against the stored SHA-256 commitment, so a wrong witness is rejected.
- All group elements are validated: they must lie in the order-q subgroup, and z₁ and z₂ must lie in Z_q.

All of these properties are covered by automated tests.

### 5.8 Data minimisation with the AI service
- **The AI is off by default.** Nothing is sent to OpenAI unless `OPENAI_API_KEY` is set.
- **Only business-planning fields are sent:** never the user's name, email, phone or account details.
- **Confidential ideas:** the description and target customers are **never included**. A test checks the exact request.
- **No invented facts:** the AI must use only EmpowerHer's facts, and the prompt treats user text as data, not as instructions, to reduce prompt injection.
- **Emergencies never wait for AI:** they always get the fixed answer.

### 5.9 Web application security
- **XSS (script injection):**
  - every page inserts user and AI text with `textContent`, never `innerHTML`, and no template uses `|safe`;
  - Django's template auto-escaping stays on;
  - links to external sites use `rel="noopener noreferrer"`.
- **Input validation** on every endpoint: types, ranges, lengths, allowed choices, and finite numbers.
- **File uploads:** an 8 MB limit, a file-signature check (a "PDF" that isn't really a PDF is rejected), and downloads only through an owner-checked, decrypting endpoint marked `Cache-Control: no-store`.
- **CSRF:**
  - the API uses tokens in the `Authorization` header, which browsers don't attach automatically to cross-site requests;
  - Django's CSRF protection still applies to session logins (the admin panel).
- **Clickjacking:** `X-Frame-Options: DENY`.
- **CORS:** open only in development. In production, only the domains listed in `DJANGO_CORS_ALLOWED_ORIGINS` are allowed.

### 5.10 Users' control over their own data
- **Download my data:** the complete record as JSON, with encrypted items decrypted for the owner only.
- **Delete my account:** password-confirmed. It removes the profile, assessments, vault entries, documents and token (database cascade). A test confirms nothing remains.
- **Delete single items:** individual assessments, vault ideas and documents.
- **Change password:** logs out other sessions.

### 5.11 Production hardening (`DJANGO_DEBUG=False`)
- **Secret key:** the app **refuses to start** without a real `DJANGO_SECRET_KEY`.
- **HTTPS everywhere:**
  - HTTP is redirected to HTTPS;
  - **HSTS** for one year tells browsers to use HTTPS only;
  - cookies are **secure-only**.
- **Hidden internals:** no debug pages or stack traces; custom 404 and 500 pages; JSON-only API, with the browsable API off.
- **Static files** are served by WhiteNoise with compression and cache-busting names.
- **gunicorn** runs several workers behind your HTTPS reverse proxy.
- **Deployment check:** `run_production.sh` runs Django's `check --deploy` and stops on any warning. The configuration passes it.

### 5.12 Secrets and repository hygiene
- **`.env`** (keys, secret key, API key) is git-ignored. Only `.env.example` and `.env.production.example`, which have no real values, are committed.
- **The database file** (`db.sqlite3`) is git-ignored.
- **Each installation generates its own keys** on first setup.

---

## 6. How the security is verified

| Check | Where |
| --- | --- |
| 127 automated tests | `python manage.py test` (also GitHub Actions: `.github/workflows/tests.yml`) |
| Owner isolation (ideas, documents, assessments) | `apps/idea_vault/tests.py`, `apps/documents/tests.py`, `apps/users/tests.py` |
| Confidential text not stored plain, not in report, not sent to AI | `apps/business/tests.py` |
| Paillier correctness and endpoint results | `apps/privacy/tests.py` |
| ZKP valid, tampered, wrong context, wrong witness | `apps/idea_vault/tests.py` |
| Aadhaar/GSTIN checksums, masking, fake file types | `apps/documents/tests.py` |
| Token expiry, rotation, rate limiting, password change, account deletion | `apps/users/tests.py` |
| Production configuration | `run_production.sh` → `check --deploy` |
| Measured performance | `python manage.py run_benchmarks` |

---

## 7. Honest limitations

Security is about knowing what is **not** covered as well as what is:

1. **The server holds the Fernet keys** for documents, confidential validation ideas, profile phone/city and older vault ideas. These are safe if the database is stolen, but the server operator could decrypt them. **New Idea Vault entries are end-to-end encrypted** in the browser, so not even the operator can read them; if the owner forgets her vault passphrase, they cannot be recovered.
2. **Some data is stored as plain text:** normal (non-confidential) validation ideas, and the profile's name, state, stage and language. A confidential idea's name, category, location and figures also stay readable, because the report needs them.
3. **Login tokens are kept in an HttpOnly cookie**, which page scripts (even injected ones) cannot read, with CSRF protection on every change. In the database they are stored as issued, so someone with database access could use an unexpired one.
4. **Document checks** confirm number formats and checksums. Confirmation by the issuing department is possible through **DigiLocker**, but only once EmpowerHer is registered as a DigiLocker partner; it is tested against a simulated DigiLocker.
5. **Market data** comes from Census 2011, the latest district-level census. It shows relative demand, not current market size.
6. **Scheme details change.** Every scheme links to its official source and must be re-checked before applying.
7. **Not yet deployed** on a public server. It runs in Docker with PostgreSQL (`docker compose up`); SQLite suits small single-machine setups.
8. **Only the assistant is multilingual**; the rest of the interface is in English.
8. **Homomorphic encryption covers addition and scaling** (Paillier). It cannot multiply two encrypted values; that would need a scheme such as CKKS or BFV.

---

## 8. File map

The backend and frontend are separated inside `empowerher/backend/`:

```
project_p/
├── SETUP.md / README.md / EXPLAIN.md      setup, reference, this document
├── setup.sh / setup.bat                   one-command setup and run
├── run_production.sh                      production mode (gunicorn)
├── report/                                project report: Results chapter, screenshots, charts
└── empowerher/backend/
    ├── manage.py, requirements.txt, .env  Django entry point, packages, secrets
    │
    ├── config/          PROJECT SETTINGS AND SHARED HELPERS
    │   ├── settings.py        all settings (security, apps, database, static files)
    │   ├── urls.py            main routing: pages -> frontend/, /api/... -> apps/
    │   ├── authentication.py  expiring login tokens
    │   ├── crypto.py          Fernet encryption helpers
    │   └── datasets.py        loads the files in datasets/
    │
    ├── apps/            BACKEND: one folder per feature (REST API + logic + tests)
    │   ├── users/        accounts, profile, password, data export, delete account,
    │   │                 management commands (seed_demo, run_benchmarks)
    │   ├── business/     idea validation, confidential mode, AI recommendations
    │   ├── schemes/      scheme catalogue + recommender.py
    │   ├── funding/      calculator.py (EMI, affordability, PMEGP)
    │   ├── privacy/      paillier.py (homomorphic encryption) + encrypted check API
    │   ├── market/       analysis.py (census-based demand index)
    │   ├── documents/    ocr.py, validators.py, encrypted document storage
    │   ├── idea_vault/   encryption.py, zkp.py (zero-knowledge proofs)
    │   ├── assistant/    engine.py (multilingual assistant)
    │   └── safety/       helplines and guides API
    │
    ├── frontend/        FRONTEND: what users see in the browser
    │   ├── urls.py, views.py   which URL shows which page
    │   ├── templates/          one HTML page per screen (base_app.html = shared layout)
    │   └── static/js/          paillier.js (browser-side homomorphic encryption)
    │
    └── datasets/        DATA: raw downloads, processed CSVs, curated JSON
```

Inside each backend app the files follow the same pattern:

| File | Role |
| --- | --- |
| `urls.py` | API routes of the app (mounted under `/api/<prefix>/` in `config/urls.py`) |
| `views.py` | API endpoints: read the request, check permissions, call the logic, return JSON |
| logic module (`recommender.py`, `paillier.py`, `zkp.py`, `ocr.py`…) | the actual algorithm, independent of the web layer |
| `models.py` | database tables (only apps that store data) |
| `tests.py` | automated tests |
| `migrations/` | database schema history |

**How a page talks to the backend:**
1. The browser opens a page, for example `/schemes/`. `frontend/urls.py` renders `frontend/templates/schemes.html`.
2. JavaScript in that page calls the API, for example `GET /api/schemes/recommend/` with the login token.
3. `config/urls.py` routes the call to `apps/schemes/views.py`, which uses `apps/schemes/recommender.py` and returns JSON.
4. The page displays the JSON with `textContent`.
