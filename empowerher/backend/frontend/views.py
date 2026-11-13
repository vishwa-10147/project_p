"""
Page views. Each one just renders an HTML template; the page then loads
its data from the backend API (/api/...) in the browser.
"""

import hashlib
import json
from functools import lru_cache

from django.conf import settings
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import cache_control


def page(template):
    """Return a view that renders `template`."""

    def view(request):
        return render(request, template)

    view.__name__ = template.replace(".html", "") + "_page"
    return view


# Pages the installed app keeps for offline use. Pages hold no personal
# data (they fetch it from the API, which is never cached), so caching them
# is safe even on a shared phone.
OFFLINE_PAGES = ["/", "/offline/", "/safety/", "/assistant/", "/funding/", "/schemes/"]
OFFLINE_STATIC = [
    "js/auth.js", "js/pwa.js", "js/paillier.js", "js/vault-crypto.js",
    "img/logo.svg", "img/icon-192.png", "img/icon-512.png",
]


@lru_cache(maxsize=1)
def cache_version():
    """Changes whenever a cached page or file changes, so phones update."""
    digest = hashlib.sha256()
    folders = [settings.TEMPLATES_DIR, settings.BASE_DIR / "frontend" / "static"]
    for folder in folders:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                digest.update(path.name.encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


@cache_control(no_cache=True)
def service_worker(request):
    """Served at /sw.js so it can control every page of the site."""
    config = json.dumps({
        "version": cache_version(),
        "pages": OFFLINE_PAGES,
        "staticFiles": [static(name) for name in OFFLINE_STATIC],
    })
    response = render(request, "sw.js", {"config": config},
                      content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response


@cache_control(max_age=86400)
def web_manifest(request):
    return render(request, "manifest.webmanifest", content_type="application/manifest+json")
