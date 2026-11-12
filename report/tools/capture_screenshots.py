"""
Capture the report screenshots from a running EmpowerHer server.

Needs a separate tools environment (not part of the app):
    pip install playwright
and Google Chrome installed (used headlessly with its own temporary profile).

Usage:
    python manage.py seed_demo          # prints the demo witness secret
    python report/tools/capture_screenshots.py --witness <secret>

Screenshots are written to report/results/screenshots/ at 2x resolution.
"""

import argparse
import json
import os
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "report" / "results" / "screenshots"
BASE = os.environ.get("EMPOWERHER_URL", "http://localhost:8000")
USERNAME = "demo_entrepreneur"
PASSWORD = os.environ.get("DEMO_PASSWORD", "EmpowerHer@Demo2026")


def login():
    request = urllib.request.Request(
        BASE + "/api/users/login/",
        json.dumps({"username": USERNAME, "password": PASSWORD}).encode(),
        {"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(request))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--witness", required=True)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    session = login()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800}, device_scale_factor=2,
            locale="en-IN",
        )
        page = context.new_page()

        # Keep the sticky header from overlapping element screenshots.
        context.add_init_script(
            "document.addEventListener('DOMContentLoaded', () => {"
            "const s = document.createElement('style');"
            "s.textContent = 'header.app-header{position:static!important}';"
            "document.head.appendChild(s);});"
        )

        def shot_range(name, start, end, start_index=0, end_index=0):
            """Screenshot from the top of `start` to the bottom of `end`."""
            page.wait_for_timeout(400)
            box = page.evaluate(
                """([start, end, si, ei]) => {
                    const a = document.querySelectorAll(start)[si]
                        .getBoundingClientRect();
                    const b = document.querySelectorAll(end)[ei]
                        .getBoundingClientRect();
                    const x = Math.min(a.left, b.left);
                    return {x: x, y: a.top + window.scrollY,
                            width: Math.max(a.right, b.right) - x,
                            height: b.bottom - a.top};
                }""",
                [start, end, start_index, end_index],
            )
            pad = 12
            clip = {"x": max(box["x"] - pad, 0), "y": max(box["y"] - pad, 0),
                    "width": box["width"] + 2 * pad,
                    "height": box["height"] + 2 * pad}
            page.screenshot(path=OUT / f"{name}.png", full_page=True,
                            clip=clip)
            print("saved", name + ".png")

        def shot(name, selector=None, full_page=False):
            page.wait_for_timeout(400)
            path = OUT / f"{name}.png"
            if selector:
                page.locator(selector).first.screenshot(path=path)
            else:
                page.screenshot(path=path, full_page=full_page)
            print("saved", path.name)

        # 1. Home page (logged out)
        page.goto(BASE + "/")
        shot("01_home")

        # Log in by storing the session the way the login page does.
        page.evaluate(
            """([token, user]) => {
                localStorage.setItem('empowerher_token', token);
                localStorage.setItem('empowerher_user', JSON.stringify(user));
            }""",
            [session["token"], session["user"]],
        )

        # 2. Dashboard
        page.goto(BASE + "/dashboard/")
        shot("02_dashboard", full_page=True)

        # 3. Business validation report (confidential idea from history)
        page.goto(BASE + "/business/validation/")
        page.wait_for_selector(".history-item")
        page.locator(".history-item", has_text="Ragi").get_by_role("button", name="View Report").click()
        page.wait_for_selector("#reportPanel:not(.hidden)")
        shot_range("03_validation_report", "#reportPanel",
                   "#reportContent .report-section", 0, 0)
        shot_range("03c_validation_market_schemes",
                   "#reportContent .report-section",
                   "#reportContent .report-section", 3, 4)
        page.locator("#is_confidential").check()
        shot("03b_confidential_option", ".confidential-option")

        # 4. Scheme recommendations
        page.goto(BASE + "/schemes/")
        page.wait_for_selector("#groups input")
        page.select_option("#category", "food")
        page.fill("#amount", "300000")
        page.fill("#description", "Homemade pickles and millet snacks")
        page.check("#groups input[value=shg]")
        page.click("#recommendButton")
        page.wait_for_selector("#recommendations .card")
        page.evaluate("document.querySelectorAll('#recommendations details')"
                      ".forEach(d => d.open = false)")
        shot_range("04_scheme_recommendations", "section.panel",
                   "#recommendations .card", 0, 2)

        # 5. Funding: EMI calculator and private HE check
        page.goto(BASE + "/funding/")
        page.click("#emiForm button")
        page.wait_for_selector("#emiResult:not(.hidden)")
        shot("05_emi_calculator", "section.panel:has(#emiForm)")
        page.fill("#heIncome", "60000")
        page.fill("#heExpenses", "35000")
        page.fill("#heExisting", "2000")
        page.fill("#heProposed", "9000")
        page.click("#heButton")
        page.wait_for_selector("#heResult:not(.hidden)", timeout=60000)
        page.evaluate("document.querySelector('#heResult details').open = true")
        shot("06_private_he_check", "section.panel:has(#heForm)")

        # 6. Market analysis
        page.goto(BASE + "/market/")
        page.wait_for_function(
            "document.getElementById('district').options.length > 1")
        page.select_option("#district", "Warangal")
        page.select_option("#category", "food")
        page.click("#marketForm button")
        page.wait_for_selector("#result:not(.hidden)")
        shot("07_market_summary", "#result section:nth-of-type(1)")
        shot("08_market_indicators", "#indicatorPanel")
        shot("09_market_ecosystem", "#result section:nth-of-type(4)")

        # 7. Documents
        page.goto(BASE + "/documents/")
        page.wait_for_selector("#documents .card")
        shot("10_document_verification", "section.panel:has(#documents)")

        # 8. Idea Vault proof and public verification
        page.goto(BASE + "/vault/")
        page.wait_for_selector("#ideas .card")
        page.locator("#ideas .card button", has_text="Create proof").click()
        page.fill("#proofWitness", args.witness)
        page.fill("#context", "Shared with WE Hub mentors for pitch review, Nov 2026")
        page.click("#proofForm button")
        page.wait_for_selector("#proofResult:not(.hidden)")
        proof = page.input_value("#proofJson")
        shot("11_vault_ideas", "section.panel:has(#ideas)")
        shot("12_vault_proof", "#proofPanel")

        verifier = context.new_page()
        verifier.goto(BASE + "/vault/verify/")
        verifier.fill("#proof", proof)
        verifier.click("#verifyForm button")
        verifier.wait_for_selector("#result:not(.hidden)")
        verifier.wait_for_timeout(400)
        verifier.locator("section.panel").first.screenshot(
            path=OUT / "13_proof_verified.png")
        print("saved 13_proof_verified.png")
        verifier.close()

        # 9. Assistant in Telugu and Hindi
        page.goto(BASE + "/assistant/")
        page.select_option("#language", "te")
        page.locator("#suggestions button").nth(1).click()
        page.wait_for_selector(".bubble.assistant >> nth=1")
        page.select_option("#language", "hi")
        page.locator("#suggestions button").nth(0).click()
        page.wait_for_selector(".bubble.assistant >> nth=2")
        # Show the whole conversation instead of a scrolled chat box.
        page.evaluate("document.getElementById('chat').style.maxHeight = 'none'")
        shot("14_assistant_multilingual", "section.panel")

        # 10. Safety
        page.goto(BASE + "/safety/")
        page.wait_for_selector("#helplines .card")
        shot("15_safety", full_page=False)

        # 11. Account security and data controls
        page.goto(BASE + "/profile/")
        page.wait_for_selector("#exportButton")
        shot_range("17_account_controls", "section.panel:has(#passwordForm)",
                   "section.panel:has(#deleteForm)")

        # 12. Mobile view
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2,
            is_mobile=True,
        )
        phone = mobile.new_page()
        phone.goto(BASE + "/")
        phone.evaluate(
            """([token, user]) => {
                localStorage.setItem('empowerher_token', token);
                localStorage.setItem('empowerher_user', JSON.stringify(user));
            }""",
            [session["token"], session["user"]],
        )
        phone.goto(BASE + "/funding/")
        phone.wait_for_timeout(500)
        phone.screenshot(path=OUT / "16_mobile_funding.png")
        print("saved 16_mobile_funding.png")

        browser.close()


if __name__ == "__main__":
    main()
