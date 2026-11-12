"""
Build the "Results" chapter of the EmpowerHer project report.

Outputs (in report/):
  - results_chapter.docx                    editable chapter for the Word source
  - results_chapter.pdf                     the same chapter as PDF
  - final_project-report_with_results.pdf   original report with the chapter
                                            inserted before "Conclusion"

Needs a tools environment:
    pip install python-docx reportlab pypdf pillow
    python report/tools/build_results_section.py

Inputs: report/results/benchmarks.json (python manage.py run_benchmarks),
report/results/screenshots/ (capture_screenshots.py) and
report/results/charts/ (make_charts.py).
"""

import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
REPORT = ROOT / "report"
RESULTS = REPORT / "results"
SHOTS = RESULTS / "screenshots"
CHARTS = RESULTS / "charts"
# Copy of the original Stage-1 report that the chapters are inserted into.
ORIGINAL_PDF = REPORT / "source" / "final_project-report-original.pdf"
CONCLUSION_PAGE_INDEX = 27  # zero-based page index of "4. CONCLUSION"

B = json.loads((RESULTS / "benchmarks.json").read_text())


TEST_COUNT = sum(
    path.read_text().count("    def test_")
    for path in (ROOT / "empowerher" / "backend" / "apps").glob("*/tests.py")
)


def ms(value):
    return f"{value:,.3f} ms" if value < 1 else f"{value:,.1f} ms"


# ---------------------------------------------------------------------
# Chapter content (rendered to both DOCX and PDF)
# ---------------------------------------------------------------------
# Block types:
#   ("h1", text) ("h2", text) ("p", text) ("bullets", [text, ...])
#   ("fig", path, caption, width_inches)
#   ("table", caption, header, rows, column_width_fractions)

fig_no = 0
tab_no = 0


def fig(path, caption, width=6.0):
    global fig_no
    fig_no += 1
    return ("fig", path, f"Figure 4.{fig_no}: {caption}", width)


def table(caption, header, rows, widths):
    global tab_no
    tab_no += 1
    return ("table", f"Table 4.{tab_no}: {caption}", header, rows, widths)


P = B["paillier"]
Z = B["zkp"]

CONTENT = [
    ("h1", "4. RESULTS"),
    ("p", "This chapter presents the results of implementing and testing "
          "Empower-Her. The complete system described in Chapter 3 was built "
          "as a Django and Django REST Framework web application with eleven "
          "modules. Each module was tested with automated tests and "
          "manually through the web interface. Section 4.1 summarises what "
          "was implemented, Section 4.2 describes the test setup, Sections "
          "4.3 to 4.10 present the output of each module with screenshots, "
          "Section 4.11 reports performance measurements, Section 4.12 the "
          "testing results, and Section 4.13 discusses the results and "
          "their limitations."),

    ("h2", "4.1 Implementation Summary"),
    ("p", "Table 4.1 lists the modules of Empower-Her, the technique each "
          "one uses, and its status. All modules proposed in the methodology "
          "were implemented except the React frontend, which was replaced by "
          "server-rendered HTML pages that use the same REST APIs."),
    table(
        "Implemented modules of Empower-Her",
        ["Module", "Technique / data used", "Status"],
        [
            ["User registration & profile", "Django auth, expiring tokens, rate-limited login, PBKDF2 password hashing", "Implemented"],
            ["Account security & data control", "Password change, data export (JSON), account deletion", "Implemented"],
            ["Business idea validation", "Financial model, rule-based analysis, optional OpenAI LLM, confidential mode", "Implemented"],
            ["Government scheme recommendation", "25 curated schemes; eligibility rules + TF-IDF similarity (scikit-learn)", "Implemented"],
            ["Funding & loan EMI", "EMI, amortisation, affordability (FOIR), PMEGP subsidy", "Implemented"],
            ["Homomorphic encryption", "Paillier (2048-bit) in browser and server", "Implemented"],
            ["Local market demand", "Census 2011 (640 districts) + Ministry of MSME data", "Implemented"],
            ["Document verification (OCR)", "RapidOCR, pypdf; PAN, Aadhaar (Verhoeff), GSTIN checksum, Udyam, IFSC", "Implemented"],
            ["Idea Vault with ZKP", "Fernet encryption, Pedersen commitment, Okamoto/Schnorr proof", "Implemented"],
            ["Multilingual voice assistant", "English, Telugu, Hindi; Web Speech API; optional LLM", "Implemented"],
            ["Women safety", "Helplines, reporting portals, safety guides", "Implemented"],
        ],
        [0.28, 0.54, 0.18],
    ),

    ("h2", "4.2 Experimental Setup"),
    ("p", f"All results were obtained on a laptop with an Apple Silicon "
          f"({B['environment']['machine']}) processor running "
          f"{B['environment']['system'].replace('Darwin', 'macOS (Darwin')}"
          f"{')' if 'Darwin' in B['environment']['system'] else ''} and "
          f"Python {B['environment']['python']}, with SQLite as the "
          f"database. The application was started with the one-command "
          f"setup script (setup.sh / setup.bat), which creates the virtual "
          f"environment, generates encryption keys, prepares the datasets "
          f"and database, and creates a demo account. The project requires "
          f"Python 3.11 to 3.13 (the earlier requirement of Python 3.9 was "
          f"raised by the data libraries used)."),
    ("p", "The demo account belongs to a fictitious entrepreneur, 'Priya "
          "Demo', from Warangal, Telangana, at the business-idea stage. It "
          "contains two validated ideas for millet snacks (one marked "
          "confidential), one idea in the Idea Vault, and a synthetic PAN "
          "card image. No real personal data was used. The datasets used "
          "are listed in Table 4.2."),
    table(
        "Datasets used",
        ["Dataset", "Source", "Size"],
        [
            ["District indicators", "Census of India 2011, district tables", "640 districts, 118 columns"],
            ["Women entrepreneurship by state", "Ministry of MSME annexures (PIB, Feb 2024): Udyam/UAP, CGTMSE, PMEGP", "36 states/UTs"],
            ["Government schemes", "Curated from official scheme websites", "25 schemes"],
            ["Loan routes", "Curated from scheme guidelines", "9 loan products"],
            ["Safety resources", "Official helplines and portals", "7 helplines, 4 portals, 6 guides"],
        ],
        [0.28, 0.47, 0.25],
    ),

    ("h2", "4.3 User Interface and Dashboard"),
    ("p", "Figure 4.1 shows the home page that visitors see before logging "
          "in. It introduces the platform and offers registration and "
          "login. After logging in, the entrepreneur reaches the dashboard "
          "(Figure 4.2), which gives one-click access to all nine modules. "
          "Every page shares a common navigation bar, and the layout adapts "
          "to mobile screens (Figure 4.19)."),
    fig(SHOTS / "01_home.png", "Home page of Empower-Her"),
    fig(SHOTS / "02_dashboard.png", "Entrepreneur dashboard with all modules", 5.6),

    ("h2", "4.4 Business Idea Validation"),
    ("p", "The entrepreneur enters the business name, category, description, "
          "location, target customers and expected figures. Figure 4.3 shows "
          "the report for the 'Ragi Energy Bars' idea: with a selling price "
          "of Rs 120 and 600 units per month, the system calculates a "
          "monthly revenue of Rs 72,000, expenses of Rs 45,000, a profit of "
          "Rs 27,000 and a profit margin of 37.5%. The form completeness is "
          "100%. The report then lists strengths, risks and practical "
          "suggestions."),
    ("p", "This idea was submitted with the Confidential option (Figure "
          "4.4). The note at the top of the report confirms that the "
          "description and target customers were stored encrypted and were "
          "not sent to the AI service, while the figures, category and "
          "location remained available for analysis. Inspection of the "
          "database confirmed that the description and target-customer "
          "columns were empty and only Fernet ciphertext was stored."),
    fig(SHOTS / "03_validation_report.png", "Business validation report for a confidential idea", 5.6),
    fig(SHOTS / "03b_confidential_option.png", "Confidential option on the validation form", 5.6),
    ("p", "Figure 4.5 shows the second half of the report. The market "
          "section places Warangal at a demand potential index of 70.5 out "
          "of 100 (Above average) for food businesses, ranking 4th of 10 "
          "Telangana districts. The report also recommends the three most "
          "relevant government schemes: WE Hub, Stree Nidhi and PM FME."),
    fig(SHOTS / "03c_validation_market_schemes.png", "Market research and scheme recommendations inside the validation report", 5.6),

    ("h2", "4.5 Government Scheme Recommendation"),
    ("p", "Figure 4.6 shows personalised recommendations for a food-business "
          "idea in Telangana at the idea stage, needing Rs 3,00,000, by a "
          "Self-Help Group member, described as 'homemade pickles and "
          "millet snacks'. The recommender first applies eligibility rules "
          "(state, business stage and social group), then scores the "
          "remaining schemes using category, amount and TF-IDF text "
          f"similarity. The top results were PM FME (score "
          f"{B['recommender']['top_3'][0]['score']}), Stree Nidhi "
          f"({B['recommender']['top_3'][1]['score']}) and WE Hub "
          f"({B['recommender']['top_3'][2]['score']}). PM FME ranks first "
          "because it is designed for food processing, covers the amount "
          "needed, targets SHG members and matches words in the "
          "description. Each card lists these reasons, so the user can see "
          "why a scheme was suggested. Schemes that are reserved for groups "
          "the user does not belong to are excluded."),
    fig(SHOTS / "04_scheme_recommendations.png", "Personalised government scheme recommendations with reasons", 5.6),

    ("h2", "4.6 Funding, EMI and Privacy-Preserving Affordability Check"),
    ("p", "Figure 4.7 shows the EMI calculator for a loan of Rs 5,00,000 at "
          "10.5% per year for 60 months. The EMI is Rs 10,747 with a total "
          "interest of Rs 1,44,817. A year-by-year schedule and the loan "
          "routes that cover this amount are also shown. The EMI matches "
          "the standard reducing-balance formula; an independent check "
          f"(Rs 5,00,000 at 10% for 36 months gives Rs {B['emi']['example']['emi']:,.2f}) "
          "is part of the automated tests."),
    fig(SHOTS / "05_emi_calculator.png", "EMI calculator with repayment schedule", 5.2),
    ("p", "Figure 4.8 shows the privacy-preserving affordability check "
          "using Paillier homomorphic encryption. The browser generated a "
          "2048-bit key pair, encrypted the monthly income (Rs 60,000), "
          "expenses (Rs 35,000) and existing EMIs (Rs 2,000), and sent only "
          "the public key and ciphertexts to the server. The 'What the "
          "server received' panel shows that the server saw only 4096-bit "
          "ciphertexts. The server computed the surplus and EMI headroom "
          "directly on the ciphertexts. After decryption in the browser, "
          "the results were a monthly surplus of Rs 25,000, a yearly "
          "surplus of Rs 3,00,000, total EMIs of Rs 11,000 and an EMI "
          "headroom of Rs 1,500. All four match the plaintext calculation, "
          "showing that the server can compute on financial data that it "
          "cannot read."),
    fig(SHOTS / "06_private_he_check.png", "Private affordability check using homomorphic encryption", 5.6),

    ("h2", "4.7 Local Market Demand Analysis"),
    ("p", "The market module compares a district with all 640 Indian "
          "districts using census indicators chosen for the business "
          "category. Figure 4.9 shows the result for food businesses in "
          "Warangal: a demand potential index of 70.5 (Above average), rank "
          "4 of 10 in Telangana, with a population of 35,12,576 and "
          "10,46,987 households (Census 2011)."),
    fig(SHOTS / "07_market_summary.png", "Market demand summary for Warangal (food and beverages)", 5.6),
    ("p", "Figure 4.10 explains the score. For food businesses the index "
          "weights population (30%), urban households (25%), working women, "
          "higher-income households and two-wheeler ownership (15% each). "
          "Warangal is in the 87th national percentile for population and "
          "for working women, but only the 42nd for higher-income "
          "households, which suggests that affordable pricing suits this "
          "market."),
    fig(SHOTS / "08_market_indicators.png", "Indicators behind the demand potential index", 5.6),
    ("p", "Figure 4.11 shows the women-entrepreneurship ecosystem in "
          "Telangana from Ministry of MSME data: 5,79,210 women-owned MSMEs, "
          "or 33.12 per 1,000 women against a national average of 23.84, "
          "together with 45,803 CGTMSE guarantees and 5,963 PMEGP projects "
          "for women. The system interprets this as a stronger support "
          "ecosystem but also more competition."),
    fig(SHOTS / "09_market_ecosystem.png", "Women entrepreneurship ecosystem in Telangana", 5.6),
    ("p", "Figure 4.12 compares all business categories for Warangal. "
          "Retail (77.9), food (70.5) and local services (69.6) have the "
          "highest demand potential, while beauty and personal care (49.3) "
          "is just below the national middle. This helps an entrepreneur "
          "choose or position a business before investing."),
    fig(CHARTS / "chart_warangal_demand.png", "Demand potential index for each business category in Warangal", 5.6),

    ("h2", "4.8 Document Verification using OCR"),
    ("p", "Figure 4.13 shows the result of uploading a synthetic PAN card "
          "image. The OCR engine read the card with "
          f"{B['ocr']['confidence'] * 100:.1f}% confidence, detected the "
          "document type as a PAN card automatically, validated the PAN "
          "structure, identified the holder type as 'Individual', and "
          "confirmed that the name on the card matches the user's profile. "
          "Only the masked number (ABXXX1234K) is stored; the original file "
          "and the full OCR text are encrypted. For Aadhaar cards the "
          "system validates the Verhoeff checksum and keeps only the last "
          "four digits, and for GSTINs it verifies the check character."),
    fig(SHOTS / "10_document_verification.png", "Document verification result for a PAN card", 5.6),

    ("h2", "4.9 Idea Vault with Zero-Knowledge Proof"),
    ("p", "Figure 4.14 shows an idea registered in the Idea Vault. The idea "
          "text is encrypted, and a Pedersen commitment is stored with the "
          "registration time. Figure 4.15 shows the owner generating an "
          "ownership proof for a specific recipient ('Shared with WE Hub "
          "mentors for pitch review, Nov 2026') using the witness secret "
          "that only the owner holds."),
    fig(SHOTS / "11_vault_ideas.png", "Idea registered in the Idea Vault", 5.6),
    fig(SHOTS / "12_vault_proof.png", "Generating a zero-knowledge ownership proof", 5.6),
    ("p", "Figure 4.16 shows the public verification page, which an "
          "investor or mentor can use without an account. The proof was "
          "accepted: it is valid, the commitment is registered on "
          "Empower-Her, and the registration time and recipient are shown. "
          "The verifier never sees the idea itself. In testing, proofs that "
          "were altered, or reused with a different recipient text, were "
          "rejected."),
    fig(SHOTS / "13_proof_verified.png", "Successful verification of an ownership proof", 5.6),

    ("h2", "4.10 Multilingual Assistant, Safety and Account Controls"),
    ("p", "Figure 4.17 shows the assistant answering in Telugu and Hindi. "
          "Asked in Telugu for the EMI of a Rs 5 lakh loan at 10% for 3 "
          "years, it replied with an EMI of Rs 16,134 and a total interest "
          "of Rs 80,809. Asked in Hindi which government schemes suit the "
          "user, it listed schemes matching her Telangana profile with "
          "official links. Questions can also be spoken through the "
          "microphone button, and answers read aloud. Without an AI key the "
          "assistant answers only from Empower-Her's verified data, which "
          "avoids invented schemes or numbers."),
    fig(SHOTS / "14_assistant_multilingual.png", "Assistant answering in Telugu and Hindi", 5.6),
    ("p", "Figure 4.18 shows the Women Safety module with a prominent "
          "emergency call button (112), national helplines and the "
          "Telangana SHE Teams route (Dial 100) for Telangana users, reporting "
          "portals and practical safety guides. Figure 4.19 shows the "
          "funding page on a mobile phone, demonstrating the responsive "
          "layout."),
    fig(SHOTS / "15_safety.png", "Women Safety module"),
    fig(SHOTS / "16_mobile_funding.png", "Funding page on a mobile phone", 2.6),
    ("p", "Figure 4.20 shows the account controls on the profile page. "
          "Users can change their password (which logs out other "
          "sessions), download all their data as a JSON file with their "
          "confidential and Idea Vault ideas decrypted for them, and "
          "permanently delete their account and all associated data after "
          "confirming their password. Login sessions expire after seven "
          "days, and login attempts are limited to ten per minute to "
          "slow down password guessing."),
    fig(SHOTS / "17_account_controls.png", "Password change, data export and account deletion", 5.6),

    ("h2", "4.11 Performance Results"),
    ("p", "The performance of each operation was measured with the "
          "run_benchmarks command; Table 4.3 and Figure 4.21 report the "
          "median time over repeated runs. Everyday operations such as "
          "Fernet encryption, EMI calculation, scheme recommendation and "
          "market analysis complete in under 5 milliseconds. The "
          "cryptographic operations (Paillier and ZKP) take between 30 and "
          "500 milliseconds because they use 2048-bit numbers. This is "
          "acceptable for interactive use: the complete private "
          "affordability check, including key generation in the browser, "
          "finished in about 1.2 seconds."),
    table(
        "Measured performance (median of repeated runs)",
        ["Operation", "Median time", "Notes"],
        [
            ["Fernet encryption of a 1 KB idea", ms(B["fernet"]["encrypt"]["median_ms"]),
             f"{B['fernet']['plaintext_bytes']} B -> {B['fernet']['ciphertext_bytes']} B ciphertext"],
            ["Fernet decryption", ms(B["fernet"]["decrypt"]["median_ms"]), "Authenticated (HMAC-SHA256)"],
            ["Paillier key generation (2048-bit)", ms(P["keygen"]["median_ms"]), "Done once per check"],
            ["Paillier encryption of one value", ms(P["encrypt_one_value"]["median_ms"]), "4096-bit ciphertext"],
            ["Affordability computed on ciphertexts", ms(P["server_affordability_computation"]["median_ms"]),
             f"Decrypted result {P['check']['decrypted']:,} = expected {P['check']['expected']:,}"],
            ["Paillier decryption of one value", ms(P["decrypt_one_value"]["median_ms"]), ""],
            ["ZKP commitment", ms(Z["commit"]["median_ms"]), "2048-bit group (RFC 3526)"],
            ["ZKP proof generation", ms(Z["prove"]["median_ms"]), f"Proof size {Z['proof_size_bytes']:,} bytes"],
            ["ZKP proof verification", ms(Z["verify"]["median_ms"]), "Tampered and replayed proofs rejected"],
            ["OCR of a PAN card image", ms(B["ocr"]["time"]["median_ms"]),
             f"{B['ocr']['confidence'] * 100:.1f}% confidence"],
            ["Scheme recommendation", ms(B["recommender"]["time"]["median_ms"]), "25 schemes"],
            ["Market analysis", ms(B["market"]["time"]["median_ms"]), "640 districts"],
            ["EMI and schedule", ms(B["emi"]["time"]["median_ms"]), ""],
        ],
        [0.42, 0.18, 0.40],
    ),
    fig(CHARTS / "chart_operation_times.png", "Median time per operation (logarithmic scale)", 5.6),

    ("h2", "4.12 Testing Results"),
    ("p", f"The system has {TEST_COUNT} automated tests covering every module, "
          f"and all {TEST_COUNT} pass (Figure 4.22). The tests check correctness, such as EMI "
          "values, Paillier homomorphic results, ZKP verification, OCR "
          "field extraction and Aadhaar and GSTIN checksums. They also check "
          "security: owner-only access to ideas and documents, rejection of "
          "tampered proofs and fake file types, masking of identity "
          "numbers, that confidential ideas are never sent to the AI "
          "service, expiry of login sessions, rate limiting of logins, and "
          "complete removal of data when an account is deleted. In addition, the setup script was tested on a fresh "
          "copy of the project: it installed everything, rebuilt the "
          "datasets from the raw downloads, ran all tests and started the "
          "server in about one minute."),
    fig(CHARTS / "chart_tests_per_module.png", "Automated tests per module", 5.4),

    ("h2", "4.13 Discussion"),
    ("p", "The results show that Empower-Her meets the objectives stated in "
          "Chapter 1. It provides a single web application for "
          "business-idea validation, scheme and funding discovery, market "
          "insight and personalised guidance. It also shows that "
          "privacy-preserving techniques can be used in practice: "
          "homomorphic encryption allowed loan affordability to be "
          "computed without revealing income, and zero-knowledge proofs "
          "allowed ownership of an idea to be proven without disclosing it, "
          "both within interactive response times."),
    ("p", "The results also have limitations:"),
    ("bullets", [
        "The market indicators come from Census 2011, the latest "
        "district-level census, so they show relative demand between "
        "districts, not current market size.",
        "Scheme details change over time and must be confirmed on the "
        "official websites linked from each scheme.",
        "Document checks confirm the format and checksums of numbers, not "
        "the authenticity of the document with the issuing authority.",
        "The server holds the encryption keys for stored ideas and "
        "documents. This protects against database leaks and against "
        "verifiers, but not against the server operator.",
        "Performance was measured on a single laptop with synthetic data, "
        "not under multi-user load, and the system has not yet been "
        "deployed on a public server.",
    ]),
]


# ---------------------------------------------------------------------
# Chapter 5: Conclusion and Future Scope (replaces the Stage-1 text,
# which described the modules as still under development)
# ---------------------------------------------------------------------

CONCLUSION = [
    ("h1", "5. CONCLUSION AND FUTURE SCOPE"),
    ("h2", "5.1 CONCLUSION"),
    ("p", "Empower-Her has been implemented as a privacy-preserving AI "
          "framework that supports women entrepreneurs from the idea stage "
          "to running a business. All the modules proposed in the "
          "methodology have been built into a single Django and Django REST "
          "Framework web application: business idea validation with "
          "census-based market indicators and scheme matching, "
          "recommendation of 25 central and state government schemes, "
          "funding tools for EMI, loan affordability and PMEGP subsidy, "
          "local market demand analysis for all 640 Indian districts, "
          "OCR-based document verification, a multilingual assistant in "
          "English, Telugu and Hindi with voice input and output, and women "
          "safety resources."),
    ("p", "The project shows that privacy-preserving techniques can be "
          "applied in a practical, interactive system. Paillier homomorphic "
          "encryption allowed loan affordability to be computed on "
          "encrypted income and expense figures that the server never sees. "
          "Pedersen commitments with a Schnorr-style zero-knowledge proof "
          "allow an entrepreneur to prove ownership of a registered idea to "
          "an investor or mentor without revealing it. Confidential ideas "
          "and identity documents are encrypted at rest, identity numbers "
          "are masked, and confidential text is never sent to external AI "
          "services. Users can export or permanently delete their data, and "
          "logins expire and are rate limited."),
    ("p", f"All {TEST_COUNT} automated tests pass. Everyday operations such as "
          "scheme recommendation and market analysis complete in under 5 "
          "milliseconds, and the cryptographic operations take between 30 "
          "and 500 milliseconds, so the complete private affordability "
          "check finishes in about 1.2 seconds in the browser. Empower-Her "
          "therefore meets its objectives: it brings validation, "
          "opportunities, market insight and guidance together in one "
          "accessible platform, while protecting the confidential "
          "information that women entrepreneurs need to share."),
    ("p", "The evaluation was carried out on a single machine with synthetic "
          "data. The market indicators are based on Census 2011, and scheme "
          "details must be confirmed on the official websites linked from "
          "the platform."),
    ("h2", "5.2 FUTURE SCOPE"),
    ("p", "Empower-Her can be extended in the following directions:"),
    ("bullets", [
        "<b>Pilot deployment:</b> deploy the platform on a public server with "
        "PostgreSQL and evaluate it with women entrepreneurs, Self-Help "
        "Groups and incubators such as WE Hub, using their feedback to "
        "improve usability.",
        "<b>End-to-end encryption:</b> encrypt ideas and documents in the "
        "browser so that even the server operator cannot read them.",
        "<b>Richer private computation:</b> use fully homomorphic schemes "
        "such as CKKS or BFV for encrypted credit scoring, and zero-knowledge "
        "range proofs to prove eligibility conditions (for example, income "
        "below a scheme limit) without revealing the actual values.",
        "<b>Official document verification:</b> verify documents with the "
        "issuing authorities through DigiLocker or authorised APIs, instead "
        "of format and checksum checks only.",
        "<b>Live data:</b> update scheme information automatically from "
        "official sources, and replace Census 2011 indicators with the next "
        "census and current Udyam registration data.",
        "<b>Wider reach:</b> add more Indian languages and a lightweight "
        "mobile app that works on low-bandwidth connections for rural "
        "users.",
        "<b>Learning from outcomes:</b> train machine-learning models on "
        "real business outcomes to improve idea validation, and connect "
        "entrepreneurs with mentors and investors on the platform.",
    ]),
]


# ---------------------------------------------------------------------
# DOCX renderer
# ---------------------------------------------------------------------

def build_docx(path, content=None):
    content = CONTENT if content is None else content
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt

    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.27), Inches(11.69)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(1))

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)

    def run_font(run, size, bold=False):
        run.font.name = "Times New Roman"
        run.font.size = Pt(size)
        run.bold = bold

    for block in content:
        kind = block[0]
        if kind in ("h1", "h2"):
            para = doc.add_paragraph()
            run_font(para.add_run(block[1]), 16 if kind == "h1" else 14, True)
            para.paragraph_format.space_before = Pt(12)
            para.paragraph_format.keep_with_next = True
            if kind == "h1":
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif kind == "p":
            para = doc.add_paragraph(block[1])
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        elif kind == "bullets":
            for item in block[1]:
                para = doc.add_paragraph(style="List Bullet")
                para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                # "<b>Lead-in:</b> rest" -> bold lead-in, normal rest
                match = re.match(r"<b>(.*?)</b>(.*)", item)
                parts = ([(match.group(1), True), (match.group(2), False)]
                         if match else [(item, False)])
                for text, bold in parts:
                    run_font(para.add_run(text), 12, bold)
        elif kind == "fig":
            _, image, caption, width = block
            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.keep_with_next = True
            para.add_run().add_picture(str(image), width=Inches(fitted_width(image, width)))
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_font(cap.add_run(caption), 11, True)
        elif kind == "table":
            _, caption, header, rows, widths = block
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.paragraph_format.keep_with_next = True
            run_font(cap.add_run(caption), 11, True)
            tbl = doc.add_table(rows=1, cols=len(header))
            tbl.style = "Table Grid"
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            for i, text in enumerate(header):
                cell = tbl.rows[0].cells[i]
                cell.text = ""
                run_font(cell.paragraphs[0].add_run(text), 11, True)
            for row in rows:
                cells = tbl.add_row().cells
                for i, text in enumerate(row):
                    cells[i].text = ""
                    run_font(cells[i].paragraphs[0].add_run(text), 10.5)
            for row in tbl.rows:
                for i, fraction in enumerate(widths):
                    row.cells[i].width = Inches(6.27 * fraction)
                    row.cells[i].paragraphs[0].paragraph_format.line_spacing = 1.0
            doc.add_paragraph()
    doc.save(path)
    print("saved", path.relative_to(ROOT))


# ---------------------------------------------------------------------
# PDF renderer
# ---------------------------------------------------------------------

MAX_FIG_HEIGHT_IN = 6.3


def fitted_width(image, width_in):
    """Shrink very tall images so they fit on one page."""
    w, h = Image.open(image).size
    return min(width_in, MAX_FIG_HEIGHT_IN * w / h)


FIRST_RESULTS_PAGE = 19          # printed number of the first Results page
PAGE_NUMBER_CENTER_X = 305.5     # matches the report's page-number position
PAGE_NUMBER_BASELINE = 33.0


def build_pdf(path, content=None, first_page=FIRST_RESULTS_PAGE,
              title="Empower-Her: Results"):
    content = CONTENT if content is None else content
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        Image as RLImage, KeepTogether, ListFlowable, ListItem, Paragraph,
        SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    font_dir = Path("/System/Library/Fonts/Supplemental")
    try:
        pdfmetrics.registerFont(TTFont("TNR", font_dir / "Times New Roman.ttf"))
        pdfmetrics.registerFont(TTFont("TNR-Bold", font_dir / "Times New Roman Bold.ttf"))
        # Lets <b>...</b> inside paragraphs use the bold face.
        pdfmetrics.registerFontFamily("TNR", normal="TNR", bold="TNR-Bold",
                                      italic="TNR", boldItalic="TNR-Bold")
        regular, bold = "TNR", "TNR-Bold"
    except Exception:
        regular, bold = "Times-Roman", "Times-Bold"

    body = ParagraphStyle("body", fontName=regular, fontSize=12, leading=18,
                          alignment=TA_JUSTIFY, spaceAfter=6)
    h1 = ParagraphStyle("h1", fontName=bold, fontSize=16, leading=22,
                        alignment=TA_CENTER, spaceAfter=12)
    h2 = ParagraphStyle("h2", fontName=bold, fontSize=14, leading=20,
                        spaceBefore=12, spaceAfter=6, keepWithNext=1)
    caption = ParagraphStyle("caption", fontName=bold, fontSize=11, leading=14,
                             alignment=TA_CENTER, spaceBefore=4, spaceAfter=12)
    cell = ParagraphStyle("cell", fontName=regular, fontSize=10.5, leading=13)
    cell_bold = ParagraphStyle("cellb", parent=cell, fontName=bold)

    story = []
    frame_width = A4[0] - 2 * inch
    for block in content:
        kind = block[0]
        if kind == "h1":
            story.append(Paragraph(block[1], h1))
        elif kind == "h2":
            story.append(Paragraph(block[1], h2))
        elif kind == "p":
            story.append(Paragraph(block[1], body))
        elif kind == "bullets":
            story.append(ListFlowable(
                [ListItem(Paragraph(item, body), leftIndent=14) for item in block[1]],
                bulletType="bullet", start="•", leftIndent=14))
        elif kind == "fig":
            _, image, text, width = block
            w, h = Image.open(image).size
            draw_w = fitted_width(image, width) * inch
            story.append(KeepTogether([
                RLImage(str(image), width=draw_w, height=draw_w * h / w),
                Paragraph(text, caption),
            ]))
        elif kind == "table":
            _, text, header, rows, widths = block
            data = [[Paragraph(c, cell_bold) for c in header]]
            data += [[Paragraph(c, cell) for c in row] for row in rows]
            tbl = Table(data, colWidths=[frame_width * f for f in widths],
                        repeatRows=1)
            tbl.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(Paragraph(text, caption))
            story.append(tbl)
            story.append(Spacer(1, 12))

    def number_page(canvas, doc):
        canvas.setFont(regular, 11)
        canvas.drawCentredString(
            PAGE_NUMBER_CENTER_X, PAGE_NUMBER_BASELINE,
            str(first_page + doc.page - 1),
        )

    SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=inch, rightMargin=inch,
        topMargin=inch, bottomMargin=inch, title=title,
    ).build(story, onFirstPage=number_page, onLaterPages=number_page)
    print("saved", path.relative_to(ROOT))


def assemble(chapter_pdf, conclusion_pdf, out_path):
    """
    Insert the Results chapter and the rewritten Conclusion, and repair
    pagination: regenerated Table of Contents, List of Figures and List of
    Tables, and continued page numbers through the References.
    """
    from report_pagination import assemble_report

    assemble_report(ORIGINAL_PDF, chapter_pdf, conclusion_pdf, out_path,
                    CONTENT, CONCLUSION, CONCLUSION_PAGE_INDEX,
                    FIRST_RESULTS_PAGE)


def main():
    from pypdf import PdfReader

    build_docx(REPORT / "results_chapter.docx")
    build_pdf(REPORT / "results_chapter.pdf")
    results_pages = len(PdfReader(str(REPORT / "results_chapter.pdf")).pages)

    build_docx(REPORT / "conclusion_chapter.docx", CONCLUSION)
    build_pdf(REPORT / "conclusion_chapter.pdf", CONCLUSION,
              first_page=FIRST_RESULTS_PAGE + results_pages,
              title="Empower-Her: Conclusion and Future Scope")

    assemble(REPORT / "results_chapter.pdf",
             REPORT / "conclusion_chapter.pdf",
             REPORT / "final_project-report_with_results.pdf")


if __name__ == "__main__":
    main()
