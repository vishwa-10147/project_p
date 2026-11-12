"""
Corrected text for the pages of the original report that are regenerated:
Abstract (page viii), List of Abbreviations (page vii), and Chapter 3
sections 3.1 and 3.2 (from page 16). Edit the text here and rebuild with
build_results_section.py.
"""

ABSTRACT = [
    "Women entrepreneurs often face challenges in accessing government "
    "schemes, securing funding, validating business ideas, and sharing "
    "sensitive information with mentors, investors, and financial "
    "institutions. Most digital platforms provide information but lack "
    "intelligent guidance and strong privacy protection, making it "
    "difficult to safeguard confidential business ideas and personal data.",

    "Empower-Her is a privacy-preserving AI framework designed to address "
    "these challenges. It uses Homomorphic Encryption to compute on "
    "sensitive financial information, such as income, expenses and loan "
    "repayments, without the server ever seeing the original values, and "
    "it encrypts identity documents and confidential business ideas at "
    "rest. It also employs Zero-Knowledge Proofs (ZKP), enabling "
    "entrepreneurs to prove ownership of their registered business ideas "
    "to investors and mentors without revealing confidential details.",

    "In addition to secure data handling, Empower-Her offers AI-powered "
    "business idea validation, personalized government scheme "
    "recommendations, local market demand analysis, multilingual voice "
    "assistance, OCR-based document verification, loan EMI estimation, and "
    "women-centric safety resources. By integrating privacy-preserving "
    "technologies with intelligent decision support, Empower-Her creates a "
    "secure and trustworthy ecosystem that helps women entrepreneurs "
    "confidently protect their innovations, access financial "
    "opportunities, and make informed business decisions.",
]

KEYWORDS = (
    "Women Entrepreneurship, Artificial Intelligence (AI), Homomorphic "
    "Encryption, Zero-Knowledge Proofs (ZKP), Business Idea Validation, "
    "Government Scheme Recommendation, Market Demand Analysis, Multilingual "
    "Voice Assistance, Optical Character Recognition (OCR), Loan EMI "
    "Estimation, Privacy-Preserving Technologies, Document Verification, "
    "Women's Safety."
)

# Original 12 abbreviations plus those used in the Results and later
# chapters. Kept in alphabetical order.
ABBREVIATIONS = sorted([
    ("AI", "Artificial Intelligence"),
    ("API", "Application Programming Interface"),
    ("BFV", "Brakerski/Fan-Vercauteren (homomorphic encryption scheme)"),
    ("CGTMSE", "Credit Guarantee Fund Trust for Micro and Small Enterprises"),
    ("CKKS", "Cheon-Kim-Kim-Song (homomorphic encryption scheme)"),
    ("CSS", "Cascading Style Sheets"),
    ("DRF", "Django REST Framework"),
    ("EMI", "Equated Monthly Instalment"),
    ("FOIR", "Fixed Obligation to Income Ratio"),
    ("GSTIN", "Goods and Services Tax Identification Number"),
    ("HE", "Homomorphic Encryption"),
    ("HMAC", "Hash-based Message Authentication Code"),
    ("HSTS", "HTTP Strict Transport Security"),
    ("HTML", "HyperText Markup Language"),
    ("HTTPS", "HyperText Transfer Protocol Secure"),
    ("IFSC", "Indian Financial System Code"),
    ("JSON", "JavaScript Object Notation"),
    ("LLM", "Large Language Model"),
    ("ML", "Machine Learning"),
    ("MSME", "Micro, Small and Medium Enterprises"),
    ("NLP", "Natural Language Processing"),
    ("OCR", "Optical Character Recognition"),
    ("PAN", "Permanent Account Number"),
    ("PBKDF2", "Password-Based Key Derivation Function 2"),
    ("PIB", "Press Information Bureau"),
    ("PMEGP", "Prime Minister's Employment Generation Programme"),
    ("PM FME", "PM Formalisation of Micro Food Processing Enterprises"),
    ("REST", "Representational State Transfer"),
    ("SC/ST", "Scheduled Castes / Scheduled Tribes"),
    ("SHA", "Secure Hash Algorithm"),
    ("SHG", "Self-Help Group"),
    ("TF-IDF", "Term Frequency-Inverse Document Frequency"),
    ("UAP", "Udyog Aadhaar Portal"),
    ("ZKP", "Zero-Knowledge Proof"),
], key=lambda pair: pair[0].upper())


# Chapter 3, sections 3.1 and 3.2 (the chapter's first page with the
# introduction and Figure 3.1 is kept from the original report).
CHAPTER3 = [
    ("h2", "3.1 Technologies Used:"),
    ("p", "The Empower-Her system was implemented with the following "
          "programming language, frameworks, libraries, cryptographic "
          "techniques and tools."),
    ("h3", "Python"),
    ("p", "Python 3.12 is the programming language of the backend. It is "
          "used for request handling, data processing, recommendation "
          "generation, document processing and the cryptographic "
          "algorithms. The project supports Python 3.11 to 3.13."),
    ("h3", "Django and Django REST Framework"),
    ("p", "Django 5.2 is the web framework. It manages user registration, "
          "authentication, access control, database interactions and the "
          "web pages. Django REST Framework provides the REST APIs under "
          "/api/ through which every page loads and submits its data. "
          "Logins use tokens that expire after seven days and are rate "
          "limited. The code is organised into eleven Django apps, one per "
          "feature, kept separate from the frontend pages."),
    ("h3", "Artificial Intelligence and Machine Learning"),
    ("p", "Government schemes are recommended by combining eligibility "
          "rules (state, business stage, social group and amount) with "
          "TF-IDF text similarity from scikit-learn between the user's "
          "business description and each scheme. Business idea validation "
          "combines a financial model, rule-based analysis and census "
          "market indicators. When an API key is configured, an OpenAI "
          "Large Language Model adds written recommendations and "
          "conversational answers, using only the facts supplied by "
          "Empower-Her; without a key, the system answers from its own "
          "data."),
    ("h3", "Privacy and Security Technologies"),
    ("bullets", [
        "<b>Homomorphic Encryption:</b> the Paillier cryptosystem with "
        "2048-bit keys, implemented in Python on the server and in "
        "JavaScript in the browser. The server computes loan "
        "affordability on encrypted income and expense figures.",
        "<b>Zero-Knowledge Proofs:</b> Pedersen commitments with an "
        "Okamoto (Schnorr-style) proof of knowledge, made non-interactive "
        "with the Fiat-Shamir method, in the 2048-bit group of RFC 3526. "
        "They prove ownership of a registered idea without revealing it.",
        "<b>Encryption at rest:</b> Fernet (AES-128 with HMAC-SHA256) "
        "encrypts confidential ideas, uploaded documents and their OCR "
        "text, using separate keys.",
        "<b>Application security:</b> PBKDF2 password hashing, expiring "
        "tokens, rate limiting, owner-only data access, and HTTPS, HSTS "
        "and secure cookies in production.",
    ]),
    ("h3", "Optical Character Recognition (OCR)"),
    ("p", "RapidOCR, which runs PaddleOCR models on ONNX Runtime, extracts "
          "text from document images, and pypdf extracts text from PDF "
          "files. The extracted numbers are validated: the PAN format, the "
          "Aadhaar Verhoeff checksum, the GSTIN check character, and the "
          "Udyam and IFSC formats. Only masked numbers are stored."),
    ("h3", "Recommendation System and Market Analysis"),
    ("p", "Pandas and NumPy process the datasets: Census 2011 indicators for "
          "640 districts, Ministry of MSME data on women-owned enterprises "
          "by state, and a curated dataset of 25 central and state "
          "government schemes with their official sources. The market "
          "module converts census indicators into percentiles and weights "
          "them by business category to give a demand potential index."),
    ("h3", "Voice Assistance"),
    ("p", "The assistant answers in English, Telugu and Hindi. Speech "
          "recognition and speech synthesis use the Web Speech API built "
          "into browsers such as Chrome and Edge, so no additional speech "
          "software is installed on the server."),
    ("h3", "Database Management"),
    ("p", "SQLite stores user accounts, profiles, business assessments, "
          "Idea Vault entries and encrypted documents through the Django "
          "ORM. PostgreSQL can be used for larger deployments."),
    ("h3", "Frontend Development"),
    ("p", "The user interface is built with Django templates, HTML, CSS and "
          "plain JavaScript, with a responsive layout for mobile phones. "
          "This replaced the React and Bootstrap frontend considered in the "
          "proposal, so that a single Django server delivers both the pages "
          "and the APIs, which simplifies setup and deployment."),
    ("h3", "Deployment and Testing"),
    ("p", "One-command setup scripts prepare the environment, encryption "
          "keys, database and datasets on Windows, Linux and macOS. In "
          "production the application runs on the gunicorn server with "
          "WhiteNoise for static files. Each module has automated tests "
          "written with the Django test framework."),

    ("h2", "3.2 Development Process"),
    ("p", "Empower-Her was developed with a modular approach. Each feature "
          "was built as a separate Django app with its own API, logic, data "
          "and tests, and then integrated through the dashboard. The six "
          "stages of the methodology in Figure 3.1 were implemented as "
          "follows:"),
    ("bullets", [
        "<b>User input and registration:</b> account registration, login "
        "and an entrepreneur profile (state, city, business stage and "
        "preferred language) that personalises the other modules.",
        "<b>Data processing and security:</b> input validation, owner-only "
        "access, encryption of confidential data, homomorphic encryption "
        "for financial figures, and zero-knowledge proofs for ideas.",
        "<b>AI processing and analysis:</b> business idea validation, scheme "
        "recommendation, local market demand analysis and optional LLM "
        "recommendations.",
        "<b>Document processing and verification:</b> OCR of identity and "
        "business documents with number validation and encrypted storage.",
        "<b>Additional entrepreneurial services:</b> EMI and affordability "
        "calculators, the PMEGP subsidy calculator, the multilingual "
        "assistant and women safety resources.",
        "<b>Personalised dashboard:</b> web pages for every module, "
        "reachable from a single dashboard and usable on mobile phones.",
    ]),
    ("p", "A knowledge base of government schemes, loan products, census "
          "and MSME data, and safety resources supports the recommendations "
          "and analysis. Each module was tested independently with "
          "automated tests and checked in the browser before integration. "
          "The system was then hardened for security and production use. "
          "The outcomes of this process are presented in Chapter 4."),
]
