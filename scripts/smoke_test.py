#!/usr/bin/env python3
"""
End-to-end smoke test against a running EmpowerHer server.

    python3 scripts/smoke_test.py http://localhost:8000

Uses only the Python standard library, so it runs anywhere (also in CI
against the Docker container). It signs up a throwaway account the way the
website does (HttpOnly cookie + CSRF), exercises every module's API, checks
the security headers and cookie flags, and deletes the account at the end.
"""

import http.cookiejar
import json
import secrets
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
results = []


def cookie(name):
    return next((c for c in jar if c.name == name), None)


def call(method, path, body=None, expect=200):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if method not in ("GET", "HEAD") and cookie("csrftoken"):
        request.add_header("X-CSRFToken", cookie("csrftoken").value)
        request.add_header("Referer", BASE + "/")
    try:
        with opener.open(request, timeout=60) as response:
            status, raw, headers = response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        status, raw, headers = error.code, error.read(), error.headers
    ok = status == expect
    results.append((ok, f"{method} {path} -> {status}" + ("" if ok else f" (expected {expect})")))
    try:
        return json.loads(raw) if raw else None, headers
    except ValueError:
        return raw.decode("utf-8", "replace"), headers


def check(ok, label):
    results.append((bool(ok), label))


def main():
    # Public pages and the installable-app files.
    for page in ("/", "/login/", "/register/", "/about/", "/safety/", "/offline/",
                 "/vault/verify/", "/manifest.webmanifest", "/sw.js"):
        call("GET", page)
    _, headers = call("GET", "/")
    check(headers.get("X-Content-Type-Options") == "nosniff", "nosniff header set")

    # Public APIs.
    call("GET", "/api/safety/resources/?state=Telangana")
    call("GET", "/api/schemes/")
    call("GET", "/api/market/analysis/?state=Telangana&category=food")
    emi, _ = call("POST", "/api/funding/emi/",
                  {"principal": 500000, "annual_rate": 10, "tenure_months": 36})
    check(emi and round(emi.get("emi", 0)) == 16134, "EMI for 5 lakh at 10% for 3 years is Rs 16,134")
    call("GET", "/api/users/profile/", expect=401)

    # Sign up like the website: token only in an HttpOnly cookie.
    username = "smoke_" + secrets.token_hex(4)
    password = "Sm0ke-" + secrets.token_urlsafe(12)
    registered, _ = call("POST", "/api/users/register/", {
        "username": username, "email": f"{username}@example.test",
        "password": password, "password_confirm": password,
        "first_name": "Smoke", "last_name": "Test", "state": "Telangana",
        "city": "Warangal", "phone_number": "9000000000", "session": "cookie",
    }, expect=201)
    check(registered and "token" not in registered, "token is not in the response body")
    auth = cookie("empowerher_auth")
    check(auth is not None and auth.has_nonstandard_attr("HttpOnly"), "login cookie is HttpOnly")

    # Logged-in APIs.
    profile, _ = call("GET", "/api/users/profile/")
    check(profile and profile["profile"]["city"] == "Warangal", "encrypted city reads back")
    call("PATCH", "/api/users/profile/", {"preferred_language": "ta"})
    call("GET", "/api/schemes/recommend/")
    alerts, _ = call("GET", "/api/schemes/alerts/")
    check(alerts and alerts["enabled"], "scheme alerts on by default")
    chat, _ = call("POST", "/api/assistant/chat/",
                   {"message": "எனக்குப் பொருந்தும் அரசு திட்டங்கள் எவை?", "language": "ta"})
    check(chat and chat["intent"] == "schemes", "Tamil question understood")
    call("POST", "/api/business/validate/", {
        "business_name": "Smoke Snacks", "category": "food", "state": "Telangana",
        "location": "Warangal", "description": "Millet snacks for offices",
        "target_customers": "Office workers", "investment": 200000,
        "selling_price": 50, "expected_monthly_sales": 1000,
        "estimated_monthly_expenses": 20000,
    }, expect=201)
    call("GET", "/api/documents/")
    call("GET", "/api/documents/digilocker/")
    vault, _ = call("GET", "/api/ideas/key/")
    check(vault is not None and vault["configured"] is False, "vault starts without a key")
    call("POST", "/api/ideas/verify-proof/", {"proof": {"commitment": "zz"}})

    # Clean up: delete the throwaway account (also clears the cookies).
    call("POST", "/api/users/delete-account/", {"password": password})
    call("GET", "/api/users/profile/", expect=401)

    failed = [label for ok, label in results if not ok]
    for ok, label in results:
        print(("PASS " if ok else "FAIL ") + label)
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
