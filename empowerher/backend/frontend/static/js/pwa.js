/* Registers the EmpowerHer service worker (installable app + offline pages). */
"use strict";

if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", function () {
        navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {
            /* The site works normally without it. */
        });
    });
}
