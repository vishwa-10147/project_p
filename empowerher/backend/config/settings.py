
"""
Django settings for EmpowerHer project.

EmpowerHer:
A Privacy-Preserving AI Framework for Women Entrepreneurship.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local secrets (encryption keys, API keys) from backend/.env.
load_dotenv(BASE_DIR / ".env")

# Security: use environment variables for deployment.
# Rotate the previously exposed development SECRET_KEY before deployment.
from django.core.exceptions import ImproperlyConfigured  # noqa: E402

DEV_SECRET_KEY = "django-insecure-local-development-only-change-before-deployment"


def env_bool(name, default):
    return os.environ.get(name, str(default)).strip().lower() in (
        "1", "true", "yes", "on"
    )


def env_list(name, default=""):
    return [
        item.strip()
        for item in os.environ.get(name, default).split(",")
        if item.strip()
    ]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or DEV_SECRET_KEY
# Debug mode is OFF unless DJANGO_DEBUG=True is set (setup.sh / setup.bat
# write it into the local .env), so a forgotten setting never exposes
# debug pages in production.
DEBUG = env_bool("DJANGO_DEBUG", False)

if not DEBUG and SECRET_KEY == DEV_SECRET_KEY:
    raise ImproperlyConfigured(
        "Set DJANGO_SECRET_KEY for production, or set DJANGO_DEBUG=True "
        "in backend/.env for local development."
    )
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# Needed for HTTPS deployments, e.g. "https://empowerher.example.org".
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    # Django defaults
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party apps
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",

    # Existing EmpowerHer apps
    "apps.users",
    "apps.business",
    "apps.schemes",
    "apps.funding",
    "apps.privacy",
    "apps.documents",
    "apps.assistant",
    "apps.safety",

    # New app
    "apps.idea_vault",
    "apps.market",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves static files efficiently in production.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "frontend" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite by default (no setup needed). For production set DATABASE_URL,
# e.g. postgres://user:password@host:5432/empowerher
DATABASES = {
    "default": dj_database_url.parse(
        # An empty DATABASE_URL also means SQLite.
        os.environ.get("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=int(os.environ.get("DJANGO_DB_CONN_MAX_AGE", "60")),
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "frontend" / "static"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # Compressed, cache-busting file names in production
        # (requires `manage.py collectstatic`).
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG else
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

# Any origin in development; only the listed origins in production.
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS")

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "config.authentication.ExpiringTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Every endpoint gets a generous overall limit (per IP for visitors,
    # per account for logged-in users); expensive endpoints get tighter
    # scoped limits on top of that.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("DJANGO_ANON_RATE", "120/minute"),
        "user": os.environ.get("DJANGO_USER_RATE", "600/minute"),
        # Login and registration.
        "auth": os.environ.get("DJANGO_AUTH_RATE", "10/minute"),
        # Public proof verification.
        "public": os.environ.get("DJANGO_PUBLIC_RATE", "60/minute"),
        # AI assistant and idea validation (may call the OpenAI API).
        "ai": os.environ.get("DJANGO_AI_RATE", "20/minute"),
        # Document uploads (OCR is CPU-heavy).
        "uploads": os.environ.get("DJANGO_UPLOAD_RATE", "10/minute"),
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Uploaded documents are encrypted at rest; keep uploads small.
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Curated datasets (schemes, loans, safety resources, market data).
DATASETS_DIR = BASE_DIR / "datasets"

# Login sessions (API tokens) expire after this many hours.
TOKEN_TTL_HOURS = int(os.environ.get("DJANGO_TOKEN_TTL_HOURS", "168"))

# ---------------------------------------------------------------------
# Production security (applied when DJANGO_DEBUG=False)
# ---------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", True)
    CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", True)
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_SUBDOMAINS", True)
    # Preloading is a long-term commitment to HTTPS for the whole domain,
    # so it is opt-in (DJANGO_HSTS_PRELOAD=True) and its warning is silenced.
    SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)
    if not SECURE_HSTS_PRELOAD:
        SILENCED_SYSTEM_CHECKS = ["security.W021"]
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
    # Behind a reverse proxy (nginx, Render, Railway...) that terminates TLS.
    if env_bool("DJANGO_BEHIND_PROXY", False):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
    ]

# Rate-limit counters must be shared by all gunicorn workers, so production
# uses a file-based cache (no extra server needed); development uses memory.
CACHES = {
    "default": (
        {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        if DEBUG else
        {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": os.environ.get(
                "DJANGO_CACHE_DIR", str(BASE_DIR / ".cache")
            ),
        }
    )
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
