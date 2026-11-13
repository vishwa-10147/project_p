/*
 * EmpowerHer login session helpers.
 *
 * The login token lives in an HttpOnly cookie set by the server, so no
 * script on the page (not even an injected one) can read or steal it.
 * The browser sends it automatically; this file only adds Django's CSRF
 * token to requests that change data, and keeps the non-secret display
 * details (name, username) of the signed-in user.
 */
"use strict";

const EmpowerHerAuth = (function () {
    const USER_KEY = "empowerher_user";
    const SAFE_METHODS = ["GET", "HEAD", "OPTIONS"];

    function readCookie(name) {
        const prefix = name + "=";
        const found = document.cookie.split(";")
            .map(function (part) { return part.trim(); })
            .find(function (part) { return part.indexOf(prefix) === 0; });
        return found ? decodeURIComponent(found.slice(prefix.length)) : "";
    }

    function safeStorage(action) {
        try { return action(window.localStorage); } catch (error) { return null; }
    }

    // Older versions kept the token in localStorage; remove it if present.
    safeStorage(function (store) { store.removeItem("empowerher_token"); });

    return {
        /* True while the login cookie is present (the server still decides). */
        signedIn: function () {
            return readCookie("empowerher_signed_in") === "1";
        },

        csrfToken: function () {
            return readCookie("csrftoken");
        },

        /* fetch() for EmpowerHer APIs: same-origin cookies + CSRF header. */
        fetch: function (path, options) {
            options = Object.assign({}, options || {});
            const method = (options.method || "GET").toUpperCase();
            const headers = Object.assign({}, options.headers || {});
            if (SAFE_METHODS.indexOf(method) === -1) {
                headers["X-CSRFToken"] = this.csrfToken();
            }
            options.method = method;
            options.headers = headers;
            options.credentials = "same-origin";
            return window.fetch(path, options);
        },

        user: function () {
            const raw = safeStorage(function (store) { return store.getItem(USER_KEY); });
            try { return JSON.parse(raw) || {}; } catch (error) { return {}; }
        },

        saveUser: function (user) {
            safeStorage(function (store) {
                store.setItem(USER_KEY, JSON.stringify(user || {}));
            });
        },

        /* Forget the local display details (the server clears the cookie). */
        clear: function () {
            safeStorage(function (store) { store.removeItem(USER_KEY); });
        },

        logout: async function () {
            try {
                await this.fetch("/api/users/logout/", { method: "POST" });
            } catch (error) {
                /* Sign out locally regardless. */
            }
            this.clear();
            window.location.href = "/login/";
        }
    };
}());
