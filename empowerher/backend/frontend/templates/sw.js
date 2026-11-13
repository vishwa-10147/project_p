/*
 * EmpowerHer service worker (installable app, works on poor connections).
 *
 * - Pages: network first; if the network fails, the saved copy; if there is
 *   none, the offline page. Pages contain no personal data.
 * - Static files (JS, icons): served from the cache, refreshed in the background.
 * - Public data (safety helplines, scheme list): network first, saved copy
 *   when offline, so emergency numbers are always available.
 * - Everything else under /api/ (anything personal) is never stored.
 */
"use strict";

const CONFIG = {{ config|safe }};
const CACHE = "empowerher-" + CONFIG.version;
const PUBLIC_DATA = ["/api/safety/resources/", "/api/schemes/", "/api/funding/products/"];

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open(CACHE)
            .then(function (cache) { return cache.addAll(CONFIG.pages.concat(CONFIG.staticFiles)); })
            .then(function () { return self.skipWaiting(); })
    );
});

self.addEventListener("activate", function (event) {
    event.waitUntil(
        caches.keys().then(function (names) {
            return Promise.all(names
                .filter(function (name) { return name.indexOf("empowerher-") === 0 && name !== CACHE; })
                .map(function (name) { return caches.delete(name); }));
        }).then(function () { return self.clients.claim(); })
    );
});

function networkFirst(request, fallbackUrl) {
    return fetch(request).then(function (response) {
        if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then(function (cache) { cache.put(request, copy); });
        }
        return response;
    }).catch(function () {
        return caches.match(request, { ignoreSearch: false }).then(function (saved) {
            return saved || (fallbackUrl ? caches.match(fallbackUrl) : Response.error());
        });
    });
}

function cacheFirst(request) {
    return caches.match(request).then(function (saved) {
        const refresh = fetch(request).then(function (response) {
            if (response.ok) {
                const copy = response.clone();
                caches.open(CACHE).then(function (cache) { cache.put(request, copy); });
            }
            return response;
        }).catch(function () { return saved; });
        return saved || refresh;
    });
}

self.addEventListener("fetch", function (event) {
    const request = event.request;
    if (request.method !== "GET") { return; }
    const url = new URL(request.url);
    if (url.origin !== self.location.origin) { return; }

    if (url.pathname.indexOf("/api/") === 0) {
        if (PUBLIC_DATA.indexOf(url.pathname) !== -1) {
            event.respondWith(networkFirst(request));
        }
        return;                       // personal data: straight to the network
    }
    if (url.pathname.indexOf("/admin/") === 0) { return; }
    if (request.mode === "navigate") {
        event.respondWith(networkFirst(request, "/offline/"));
        return;
    }
    if (url.pathname.indexOf("/static/") === 0) {
        event.respondWith(cacheFirst(request));
    }
});
