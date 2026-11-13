/*
 * EmpowerHer Idea Vault: end-to-end encryption and zero-knowledge proofs
 * in the browser.
 *
 *   passphrase --PBKDF2-SHA256 (600,000 rounds, per-user salt)--> AES-256-GCM key
 *
 * The idea and its witness secret are encrypted here before upload, and
 * the Pedersen commitment and ownership proofs are computed here too, so
 * the server never sees the idea, the witness or the passphrase.
 *
 * The proof maths mirrors apps/idea_vault/zkp.py, version 2 (SHA-256 hash).
 * The key is created non-extractable: scripts can use it but not export it.
 */
"use strict";

const VaultCrypto = (function () {
    const PBKDF2_ITERATIONS = 600000;
    const KEY_CHECK_TEXT = "EmpowerHer vault key check v1";
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    /* ---- RFC 3526 group 14, same constants as zkp.py ---- */
    const P = BigInt("0x" +
        "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1" +
        "29024E088A67CC74020BBEA63B139B22514A08798E3404DD" +
        "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245" +
        "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED" +
        "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D" +
        "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F" +
        "83655D23DCA3AD961C62F356208552BB9ED529077096966D" +
        "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B" +
        "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9" +
        "DE2BCBF6955817183995497CEA956AE515D2261898FA0510" +
        "15728E5A8AACAA68FFFFFFFFFFFFFFFF");
    const Q = (P - 1n) / 2n;
    const G = 4n;
    // Second generator h (derived by hashing in zkp.py; nobody knows log_g h).
    const H = BigInt("0x" +
        "afc5b271c143e51a7ac8cf1963d608e87908b7e73f28644e0c65ce9e1b1d7476" +
        "e91223db4f4e3ab44a95e6ff650f7bdc11061648db2ce7bf62a7590de2a300b5" +
        "26c4d328fb60b4ac853b3cbacae17a970fdc33a1df435c59e22733e8a6428ed6" +
        "9f49700fb3cdcf7ed60a10bcecdef56be635d38dcbc16ac3a4fef4e3a2234aa5" +
        "515b44e3baa2ee60ba249aeb82dc21e05c8b549225e68c35cded6d4b8434b07b" +
        "bc9e7d563fee42c77ffc463963192636ec92e35b85808133aad927cf8e68a01b" +
        "3e29c6351a1b9479e3333b4c515cefee2a4dfb517637f8b2fb741fcd6ea3f634" +
        "d3c6e97acfe17cec359df235ef1015c9435fa58fcca88bbe2c50b38188379458");
    const DOMAIN = encoder.encode("EmpowerHer-IdeaVault-ZKP-v2");

    /* ---- small helpers ---- */
    function toBase64(bytes) {
        let binary = "";
        bytes.forEach(function (b) { binary += String.fromCharCode(b); });
        return btoa(binary);
    }

    function fromBase64(text) {
        const binary = atob(text);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) { bytes[i] = binary.charCodeAt(i); }
        return bytes;
    }

    function hexToBytes(hex) {
        const bytes = new Uint8Array(hex.length / 2);
        for (let i = 0; i < bytes.length; i++) {
            bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
        }
        return bytes;
    }

    function bytesToHex(bytes) {
        return Array.from(bytes, function (b) {
            return b.toString(16).padStart(2, "0");
        }).join("");
    }

    function bytesToBigInt(bytes) {
        return bytes.length ? BigInt("0x" + bytesToHex(bytes)) : 0n;
    }

    function randomBytes(n) {
        return crypto.getRandomValues(new Uint8Array(n));
    }

    function concat(parts) {
        const total = parts.reduce(function (sum, p) { return sum + p.length; }, 0);
        const out = new Uint8Array(total);
        let offset = 0;
        parts.forEach(function (p) { out.set(p, offset); offset += p.length; });
        return out;
    }

    function uint32(n) {
        return new Uint8Array([(n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255]);
    }

    function modPow(base, exponent, modulus) {
        let result = 1n;
        base %= modulus;
        while (exponent > 0n) {
            if (exponent & 1n) { result = (result * base) % modulus; }
            base = (base * base) % modulus;
            exponent >>= 1n;
        }
        return result;
    }

    /* Uniform-enough random scalar in [0, q): 2048 + 128 random bits mod q. */
    function randomScalar() {
        return bytesToBigInt(randomBytes(272)) % Q;
    }

    /* Mirrors zkp._hash_to_int_v2: SHA-256 counter mode over length-prefixed parts. */
    async function hashToInt(parts, length) {
        length = length || 256;
        const data = concat(parts.map(function (part) {
            const bytes = typeof part === "string" ? encoder.encode(part)
                : (part instanceof Uint8Array ? part : encoder.encode(String(part)));
            return concat([uint32(bytes.length), bytes]);
        }));
        const blocks = [];
        for (let counter = 0; counter < length / 32; counter++) {
            const digest = await crypto.subtle.digest("SHA-256", concat([data, uint32(counter)]));
            blocks.push(new Uint8Array(digest));
        }
        return bytesToBigInt(concat(blocks));
    }

    async function ideaScalar(idea) {
        return (await hashToInt([DOMAIN, "message", encoder.encode(idea)])) % Q;
    }

    async function witnessScalar(witnessHex) {
        return (await hashToInt([DOMAIN, "blinding", hexToBytes(witnessHex)])) % Q;
    }

    /* ---- keys and AES-GCM envelopes ---- */
    async function deriveKey(passphrase, saltBase64, iterations) {
        const material = await crypto.subtle.importKey(
            "raw", encoder.encode(passphrase), "PBKDF2", false, ["deriveKey"]);
        return crypto.subtle.deriveKey(
            { name: "PBKDF2", hash: "SHA-256", salt: fromBase64(saltBase64), iterations: iterations },
            material,
            { name: "AES-GCM", length: 256 },
            false,                       // not extractable
            ["encrypt", "decrypt"]);
    }

    async function encryptText(key, text) {
        const iv = randomBytes(12);
        const ciphertext = await crypto.subtle.encrypt(
            { name: "AES-GCM", iv: iv }, key, encoder.encode(text));
        return { v: 1, alg: "AES-256-GCM", iv: toBase64(iv), ct: toBase64(new Uint8Array(ciphertext)) };
    }

    async function decryptText(key, envelope) {
        if (!envelope || envelope.v !== 1 || envelope.alg !== "AES-256-GCM") {
            throw new Error("Unsupported encryption format.");
        }
        try {
            const plain = await crypto.subtle.decrypt(
                { name: "AES-GCM", iv: fromBase64(envelope.iv) }, key, fromBase64(envelope.ct));
            return decoder.decode(plain);
        } catch (error) {
            throw new Error("Could not decrypt: wrong passphrase or damaged data.");
        }
    }

    return {
        PBKDF2_ITERATIONS: PBKDF2_ITERATIONS,

        /* New vault: random salt, derived key, and an encrypted check value. */
        createVaultKey: async function (passphrase) {
            const salt = toBase64(randomBytes(16));
            const key = await deriveKey(passphrase, salt, PBKDF2_ITERATIONS);
            const keyCheck = await encryptText(key, KEY_CHECK_TEXT);
            return { key: key, settings: { salt: salt, iterations: PBKDF2_ITERATIONS, key_check: keyCheck } };
        },

        /* Unlock: derive the key and prove it is the right one. */
        unlock: async function (passphrase, settings) {
            const key = await deriveKey(passphrase, settings.salt, settings.iterations);
            let check;
            try {
                check = await decryptText(key, settings.key_check);
            } catch (error) {
                throw new Error("Wrong vault passphrase.");
            }
            if (check !== KEY_CHECK_TEXT) { throw new Error("Wrong vault passphrase."); }
            return key;
        },

        /* Encrypt an idea with a fresh witness; return what the server stores. */
        sealIdea: async function (key, idea) {
            const witness = bytesToHex(randomBytes(32));
            const commitment = await this.commit(idea, witness);
            const envelope = await encryptText(key, JSON.stringify({ idea: idea, witness: witness }));
            return { encrypted_payload: envelope, pedersen_commitment: commitment.toString(16) };
        },

        openIdea: async function (key, envelope) {
            return JSON.parse(await decryptText(key, envelope));
        },

        /* C = g^m * h^r mod p   (zkp.commit, version 2) */
        commit: async function (idea, witnessHex) {
            const m = await ideaScalar(idea);
            const r = await witnessScalar(witnessHex);
            return (modPow(G, m, P) * modPow(H, r, P)) % P;
        },

        /* Okamoto proof of knowledge of (m, r), Fiat-Shamir, bound to context. */
        prove: async function (idea, witnessHex, context) {
            const m = await ideaScalar(idea);
            const r = await witnessScalar(witnessHex);
            const commitment = (modPow(G, m, P) * modPow(H, r, P)) % P;
            const a = randomScalar();
            const b = randomScalar();
            const t = (modPow(G, a, P) * modPow(H, b, P)) % P;
            const c = (await hashToInt([DOMAIN, "challenge", commitment.toString(), t.toString(), context])) % Q;
            return {
                commitment: commitment.toString(16),
                t: t.toString(16),
                z1: ((a + c * m) % Q).toString(16),
                z2: ((b + c * r) % Q).toString(16),
                context: context,
                version: 2
            };
        }
    };
}());
