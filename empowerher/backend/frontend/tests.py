import json

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


def exists(test, url):
    """Static files are checked on disk; pages are fetched."""
    if url.startswith("/static/"):
        test.assertIsNotNone(finders.find(url.removeprefix("/static/")), url)
    else:
        test.assertEqual(test.client.get(url).status_code, 200, url)


class InstallableAppTests(SimpleTestCase):
    def test_manifest(self):
        response = self.client.get("/manifest.webmanifest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/manifest+json")
        manifest = json.loads(response.content)
        self.assertEqual(manifest["display"], "standalone")
        sizes = {icon["sizes"] for icon in manifest["icons"]}
        self.assertTrue({"192x192", "512x512"} <= sizes)
        self.assertIn("maskable", {icon["purpose"] for icon in manifest["icons"]})
        for icon in manifest["icons"]:
            with self.subTest(icon=icon["src"]):
                exists(self, icon["src"])

    def test_service_worker_controls_the_whole_site(self):
        response = self.client.get("/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/javascript")
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertIn("no-cache", response["Cache-Control"])

    def test_service_worker_never_caches_personal_api_data(self):
        body = self.client.get("/sw.js").content.decode()
        config = json.loads(body.split("const CONFIG = ", 1)[1].split(";\n", 1)[0])
        self.assertIn("/offline/", config["pages"])
        self.assertFalse([p for p in config["pages"] if p.startswith("/api/")])
        public = body.split("const PUBLIC_DATA = ", 1)[1].split(";", 1)[0]
        for personal in ("/api/users", "/api/ideas", "/api/documents", "/api/business"):
            self.assertNotIn(personal, public)
        # Every file it pre-caches must exist, or installation would fail.
        for url in config["pages"] + config["staticFiles"]:
            with self.subTest(url=url):
                exists(self, url)

    def test_offline_page_shows_emergency_numbers(self):
        response = self.client.get("/offline/")
        self.assertContains(response, "tel:112")
        self.assertContains(response, "tel:1930")

    def test_pages_link_the_manifest(self):
        for url in ("/", "/login/", "/dashboard/", "/safety/"):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), 'rel="manifest"')
