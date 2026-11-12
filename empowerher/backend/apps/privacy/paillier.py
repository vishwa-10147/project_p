"""
Paillier additively homomorphic encryption.

    Enc(m1) * Enc(m2) mod n^2  = Enc(m1 + m2)
    Enc(m) ^ k        mod n^2  = Enc(k * m)

EmpowerHer uses it so the server can compute on a user's financial
figures without ever seeing them: the browser generates the key pair,
encrypts its numbers and sends only ciphertexts and the public key.
The server returns encrypted results that only the browser can decrypt.

The server only needs the public-key operations. Key generation and
decryption are included for tests and command-line demos; the browser
uses the matching JavaScript implementation in static/js/paillier.js.

Negative numbers are encoded modulo n (values above n/2 are negative).
"""

import secrets

MIN_KEY_BITS = 1024
MAX_KEY_BITS = 4096

_SMALL_PRIMES = [p for p in range(3, 2000, 2)
                 if all(p % d for d in range(3, int(p ** 0.5) + 1, 2))]


def _is_probable_prime(n, rounds=40):
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _random_prime(bits):
    while True:
        candidate = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(candidate):
            return candidate


class PublicKey:
    def __init__(self, n):
        if not MIN_KEY_BITS <= n.bit_length() <= MAX_KEY_BITS:
            raise ValueError(
                f"Key size must be {MIN_KEY_BITS}-{MAX_KEY_BITS} bits."
            )
        if n % 2 == 0:
            raise ValueError("Invalid Paillier modulus.")
        self.n = n
        self.n_sq = n * n

    def encode(self, value):
        return value % self.n

    def encrypt(self, value):
        m = self.encode(value)
        while True:
            r = secrets.randbelow(self.n - 1) + 1
            if _gcd(r, self.n) == 1:
                break
        # With g = n + 1: g^m = 1 + m*n (mod n^2).
        return (1 + m * self.n) * pow(r, self.n, self.n_sq) % self.n_sq

    def check_ciphertext(self, c):
        if not 0 < c < self.n_sq or _gcd(c, self.n) != 1:
            raise ValueError("Invalid ciphertext.")
        return c

    def add(self, c1, c2):
        return c1 * c2 % self.n_sq

    def add_plain(self, c, value):
        return c * (1 + self.encode(value) * self.n) % self.n_sq

    def mul_plain(self, c, k):
        if k < 0:
            return pow(pow(c, -1, self.n_sq), -k, self.n_sq)
        return pow(c, k, self.n_sq)

    def linear(self, terms, constant=0):
        """Encrypted sum of k_i * Enc(x_i) plus a plaintext constant."""
        result = self.encrypt(0)
        for ciphertext, k in terms:
            result = self.add(result, self.mul_plain(ciphertext, k))
        return self.add_plain(result, constant)


class PrivateKey:
    def __init__(self, public_key, p, q):
        self.public_key = public_key
        n = public_key.n
        self.lam = (p - 1) * (q - 1) // _gcd(p - 1, q - 1)
        self.mu = pow(self.lam, -1, n)

    def decrypt(self, c):
        n = self.public_key.n
        x = pow(c, self.lam, self.public_key.n_sq)
        m = (x - 1) // n * self.mu % n
        return m - n if m > n // 2 else m


def generate_keypair(bits=2048):
    half = bits // 2
    while True:
        p, q = _random_prime(half), _random_prime(half)
        if p != q and (p * q).bit_length() == bits:
            break
    public = PublicKey(p * q)
    return public, PrivateKey(public, p, q)


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a
