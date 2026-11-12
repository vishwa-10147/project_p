# EmpowerHer

**A privacy-preserving AI framework for women entrepreneurship.**
Django + Django REST Framework backend with server-rendered pages.

## Quick start

```bash
cd empowerher/backend
python3.12 -m venv ../../.venv            # once
../../.venv/bin/pip install -r requirements.txt
cp .env.example .env                      # then fill in the keys (see below)
../../.venv/bin/python manage.py migrate
../../.venv/bin/python manage.py runserver
```

Open http://localhost:8000, register, and use the dashboard.

Generate each encryption key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key |
| `IDEA_VAULT_ENCRYPTION_KEY` | Encrypts Idea Vault ideas (Fernet) |
| `DOCUMENT_ENCRYPTION_KEY` | Encrypts uploaded documents and their OCR text (Fernet) |
| `OPENAI_API_KEY` | Optional. Enables AI recommendations and AI assistant answers |
| `OPENAI_MODEL` | Optional, default `gpt-4.1-mini` |

Losing an encryption key makes the data encrypted with it unreadable. Back keys up separately from the database.

Run the tests:

```bash
../../.venv/bin/python manage.py test
```

## Modules

| Module | Page | API | What it does |
| --- | --- | --- | --- |
| Users | `/register/`, `/login/`, `/profile/` | `/api/users/` | Token auth; profile (state, city, stage, language) personalises other modules |
| Business validation | `/business/validation/` | `/api/business/` | Financial estimate, strengths/risks, census market indicators, matching schemes, optional AI advice |
| Schemes | `/schemes/` | `/api/schemes/` | 25 curated central/state schemes; rule + TF-IDF recommender with reasons |
| Funding | `/funding/` | `/api/funding/` | EMI + amortisation, affordability, PMEGP subsidy, loan routes |
| Private check (HE) | `/funding/` | `/api/privacy/financial-check/` | Paillier homomorphic loan-affordability check; server never sees the figures |
| Market | `/market/` | `/api/market/` | District demand-potential index per business category from Census 2011; state women-MSME ecosystem |
| Documents | `/documents/` | `/api/documents/` | OCR (RapidOCR / pypdf), PAN/Aadhaar/GSTIN/Udyam/IFSC validation, encrypted storage, masked fields |
| Idea Vault (ZKP) | `/vault/`, `/vault/verify/` | `/api/ideas/` | Encrypted ideas, Pedersen commitments, zero-knowledge ownership proofs, public verifier |
| Assistant | `/assistant/` | `/api/assistant/chat/` | English/Telugu/Hindi, text or voice (Web Speech API); knowledge-base answers, optional OpenAI |
| Safety | `/safety/` | `/api/safety/resources/` | Helplines, reporting portals, safety guides |

## Privacy technologies

### Homomorphic encryption (Paillier)
- **Server:** `privacy/paillier.py`. **Browser:** `static/js/paillier.js`.
- The browser generates a 2048-bit key pair, encrypts income, expenses and EMIs, and sends only the public key and ciphertexts.
- The server computes `Enc(surplus)`, `Enc(12 × surplus)`, `Enc(EMI headroom)` and `Enc(total EMI)` using homomorphic addition and scalar multiplication.
- Only the browser can decrypt the results. Nothing is stored.

### Zero-knowledge proof of idea ownership
- **Code:** `idea_vault/zkp.py`.
- On registration, the server stores a Pedersen commitment `C = g^m · h^r mod p`:
  - `m` is a hash of the idea;
  - `r` is derived from a witness secret given only to the owner;
  - the group is the RFC 3526 2048-bit safe-prime group.
- The owner can later create a Fiat–Shamir Okamoto proof of knowledge of `(m, r)`, bound to a context string (who the proof is for).
- Anyone can verify the proof at `/vault/verify/`. They learn that the prover registered the idea at the time shown and knows it, and nothing about its contents.

### At-rest encryption
- Ideas, uploaded files and OCR text are encrypted with Fernet (AES-128-CBC + HMAC).
- Aadhaar numbers are never stored. Only `XXXX XXXX 1234` is kept, as UIDAI rules require.
- PANs are partially masked.

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
- **The server can decrypt vault ideas.** It holds the Fernet key so it can show ideas to their owners and generate proofs. The ZKP protects the idea from verifiers (investors, mentors), not from the server operator.
- **Not ready for deployment yet.** Before deploying: set `DJANGO_DEBUG=False`, restrict `CORS_ALLOW_ALL_ORIGINS`, use PostgreSQL, and serve static files with `collectstatic`.
