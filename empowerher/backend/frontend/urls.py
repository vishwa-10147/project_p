"""
Website pages (frontend). The JSON API routes are in config/urls.py.

| URL                    | Template                  | Backend API used           |
|------------------------|---------------------------|----------------------------|
| /                      | home.html                 | -                          |
| /login/, /register/    | login.html, register.html | /api/users/                |
| /about/                | about.html                | -                          |
| /dashboard/            | dashboard.html            | -                          |
| /business/validation/  | business_validation.html  | /api/business/             |
| /schemes/              | schemes.html              | /api/schemes/              |
| /funding/              | funding.html              | /api/funding/, /api/privacy/ |
| /market/               | market.html               | /api/market/               |
| /documents/            | documents.html            | /api/documents/            |
| /vault/, /vault/verify/| vault.html, vault_verify.html | /api/ideas/            |
| /assistant/            | assistant.html            | /api/assistant/            |
| /safety/               | safety.html               | /api/safety/               |
| /profile/              | profile.html              | /api/users/                |
| /offline/              | offline.html              | - (shown when offline)     |
| /sw.js, /manifest.webmanifest | installable app (PWA) | -                      |
"""

from django.urls import path

from .views import page, service_worker, web_manifest

urlpatterns = [
    path("", page("home.html"), name="home"),
    path("login/", page("login.html"), name="login-page"),
    path("register/", page("register.html"), name="register-page"),
    path("about/", page("about.html"), name="about-page"),
    path("dashboard/", page("dashboard.html"), name="dashboard-page"),
    path("business/validation/", page("business_validation.html"),
         name="business-validation-page"),
    path("schemes/", page("schemes.html"), name="schemes-page"),
    path("funding/", page("funding.html"), name="funding-page"),
    path("market/", page("market.html"), name="market-page"),
    path("documents/", page("documents.html"), name="documents-page"),
    path("vault/", page("vault.html"), name="vault-page"),
    path("vault/verify/", page("vault_verify.html"),
         name="vault-verify-page"),
    path("assistant/", page("assistant.html"), name="assistant-page"),
    path("safety/", page("safety.html"), name="safety-page"),
    path("profile/", page("profile.html"), name="profile-page"),
    path("offline/", page("offline.html"), name="offline-page"),
    # Installable app (PWA)
    path("sw.js", service_worker, name="service-worker"),
    path("manifest.webmanifest", web_manifest, name="web-manifest"),
]
