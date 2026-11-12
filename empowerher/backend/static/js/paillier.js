/*
 * Paillier homomorphic encryption in the browser (BigInt).
 *
 * Matches privacy/paillier.py on the server: g = n + 1, negative values
 * encoded modulo n. The key pair is generated here and the private key
 * never leaves this page; the server only receives the public key and
 * ciphertexts.
 */
(function (global) {
    "use strict";

    const SMALL_PRIMES = [];
    for (let i = 3; i < 2000; i += 2) {
        let prime = true;
        for (let d = 3; d * d <= i; d += 2) {
            if (i % d === 0) { prime = false; break; }
        }
        if (prime) { SMALL_PRIMES.push(BigInt(i)); }
    }

    function randomBits(bits) {
        const bytes = new Uint8Array(Math.ceil(bits / 8));
        crypto.getRandomValues(bytes);
        let value = 0n;
        for (const byte of bytes) { value = (value << 8n) | BigInt(byte); }
        return value & ((1n << BigInt(bits)) - 1n);
    }

    function randomBelow(limit) {
        const bits = limit.toString(2).length;
        let value;
        do { value = randomBits(bits); } while (value >= limit || value === 0n);
        return value;
    }

    function modPow(base, exponent, modulus) {
        let result = 1n;
        base %= modulus;
        while (exponent > 0n) {
            if (exponent & 1n) { result = result * base % modulus; }
            base = base * base % modulus;
            exponent >>= 1n;
        }
        return result;
    }

    function gcd(a, b) {
        while (b) { [a, b] = [b, a % b]; }
        return a;
    }

    function modInverse(a, m) {
        let [oldR, r] = [((a % m) + m) % m, m];
        let [oldS, s] = [1n, 0n];
        while (r) {
            const q = oldR / r;
            [oldR, r] = [r, oldR - q * r];
            [oldS, s] = [s, oldS - q * s];
        }
        if (oldR !== 1n) { throw new Error("No modular inverse"); }
        return ((oldS % m) + m) % m;
    }

    function isProbablePrime(n, rounds) {
        for (const p of SMALL_PRIMES) {
            if (n % p === 0n) { return n === p; }
        }
        let d = n - 1n;
        let s = 0;
        while ((d & 1n) === 0n) { d >>= 1n; s += 1; }
        for (let i = 0; i < rounds; i += 1) {
            const a = randomBelow(n - 3n) + 1n;
            let x = modPow(a, d, n);
            if (x === 1n || x === n - 1n) { continue; }
            let composite = true;
            for (let j = 1; j < s; j += 1) {
                x = x * x % n;
                if (x === n - 1n) { composite = false; break; }
            }
            if (composite) { return false; }
        }
        return true;
    }

    function randomPrime(bits) {
        for (;;) {
            const candidate = randomBits(bits) | (1n << BigInt(bits - 1)) | 1n;
            if (isProbablePrime(candidate, 32)) { return candidate; }
        }
    }

    function generateKeyPair(bits) {
        bits = bits || 2048;
        let p, q, n;
        do {
            p = randomPrime(bits / 2);
            q = randomPrime(bits / 2);
            n = p * q;
        } while (p === q || n.toString(2).length !== bits);

        const lambda = (p - 1n) * (q - 1n) / gcd(p - 1n, q - 1n);
        const publicKey = { n: n, nSquared: n * n };
        const privateKey = { lambda: lambda, mu: modInverse(lambda, n), publicKey: publicKey };
        return { publicKey: publicKey, privateKey: privateKey };
    }

    function encrypt(publicKey, value) {
        const n = publicKey.n;
        const m = ((BigInt(value) % n) + n) % n;
        let r;
        do { r = randomBelow(n); } while (gcd(r, n) !== 1n);
        return (1n + m * n) % publicKey.nSquared *
            modPow(r, n, publicKey.nSquared) % publicKey.nSquared;
    }

    function decrypt(privateKey, ciphertext) {
        const { n, nSquared } = privateKey.publicKey;
        const x = modPow(BigInt(ciphertext), privateKey.lambda, nSquared);
        const m = (x - 1n) / n * privateKey.mu % n;
        return m > n / 2n ? m - n : m;
    }

    global.Paillier = {
        generateKeyPair: generateKeyPair,
        encrypt: encrypt,
        decrypt: decrypt,
        toHex: function (value) { return value.toString(16); },
        fromHex: function (hex) { return BigInt("0x" + hex); }
    };
})(window);
