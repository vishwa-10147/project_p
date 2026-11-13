"""
Zero-knowledge proof of idea ownership.

Each registered idea gets a Pedersen commitment

    C = g^m * h^r  (mod p)

where m is a hash of the idea and r is derived from the owner's private
witness. C reveals nothing about the idea, but is binding: nobody can
later open it to a different idea.

To prove ownership to an investor or mentor without revealing the idea,
the owner produces a non-interactive Okamoto (Schnorr-style) proof of
knowledge of (m, r), made non-interactive with the Fiat-Shamir
heuristic and bound to a context string (e.g. who the proof is for and
when), so it cannot be replayed for a different context:

    T  = g^a * h^b                     (a, b random)
    c  = H(C, T, context)  mod q
    z1 = a + c*m           mod q
    z2 = b + c*r           mod q

The verifier checks  g^z1 * h^z2 == T * C^c  (mod p)  and learns only
that the prover knows an opening of C.

Group: the 2048-bit MODP safe prime from RFC 3526 (group 14). We work
in its prime-order subgroup of quadratic residues (order q = (p-1)/2),
with generator g = 4 and a second generator h derived by hashing, so
nobody knows log_g(h).

Versions
--------
v1  hashes with SHAKE-256; used for ideas encrypted on the server, where
    the server builds the proof (prove()).
v2  hashes with SHA-256 in counter mode, which every browser provides
    (WebCrypto). Used for end-to-end encrypted ideas: the browser builds
    the commitment and the proof (frontend/static/js/vault-crypto.js), and
    the server only verifies. Same group, same g and h.
"""

import hashlib
import secrets

P = int(
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AACAA68FFFFFFFFFFFFFFFF",
    16,
)
Q = (P - 1) // 2
G = 4

DOMAIN = b"EmpowerHer-IdeaVault-ZKP-v1"


def _hash_to_int(*parts, length=256):
    shake = hashlib.shake_256()
    for part in parts:
        data = part if isinstance(part, bytes) else str(part).encode()
        shake.update(len(data).to_bytes(4, "big") + data)
    return int.from_bytes(shake.digest(length), "big")


DOMAIN_V2 = b"EmpowerHer-IdeaVault-ZKP-v2"


def _hash_to_int_v2(*parts, length=256):
    """SHA-256 in counter mode over length-prefixed parts (browser-friendly)."""
    data = b""
    for part in parts:
        part = part if isinstance(part, bytes) else str(part).encode()
        data += len(part).to_bytes(4, "big") + part
    output = b"".join(
        hashlib.sha256(data + counter.to_bytes(4, "big")).digest()
        for counter in range(length // 32)
    )
    return int.from_bytes(output, "big")


# Second generator: hash to the group, then square into the QR subgroup.
H = pow(_hash_to_int(DOMAIN, b"generator-h") % P, 2, P)


def _hasher(version):
    if version == 2:
        return DOMAIN_V2, _hash_to_int_v2
    return DOMAIN, _hash_to_int


def idea_scalar(idea, version=1):
    domain, hash_to_int = _hasher(version)
    return hash_to_int(domain, b"message", idea.encode("utf-8")) % Q


def witness_scalar(witness_hex, version=1):
    domain, hash_to_int = _hasher(version)
    return hash_to_int(domain, b"blinding", bytes.fromhex(witness_hex)) % Q


def commit(idea, witness_hex, version=1):
    m = idea_scalar(idea, version)
    r = witness_scalar(witness_hex, version)
    return pow(G, m, P) * pow(H, r, P) % P


def _challenge(commitment, t, context, version=1):
    domain, hash_to_int = _hasher(version)
    return hash_to_int(domain, b"challenge", commitment, t, context) % Q


def is_group_element(value):
    """True for an element of the order-q subgroup (a valid commitment)."""
    return 1 < value < P and pow(value, Q, P) == 1


def prove(idea, witness_hex, context, version=1):
    m = idea_scalar(idea, version)
    r = witness_scalar(witness_hex, version)
    commitment = pow(G, m, P) * pow(H, r, P) % P

    a = secrets.randbelow(Q)
    b = secrets.randbelow(Q)
    t = pow(G, a, P) * pow(H, b, P) % P
    c = _challenge(commitment, t, context, version)

    proof = {
        "commitment": format(commitment, "x"),
        "t": format(t, "x"),
        "z1": format((a + c * m) % Q, "x"),
        "z2": format((b + c * r) % Q, "x"),
        "context": context,
    }
    if version != 1:
        proof["version"] = version
    return proof


def verify(proof):
    try:
        commitment = int(proof["commitment"], 16)
        t = int(proof["t"], 16)
        z1 = int(proof["z1"], 16)
        z2 = int(proof["z2"], 16)
        context = str(proof["context"])
        version = int(proof.get("version", 1))
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
    if version not in (1, 2):
        return False

    # Elements must be in the order-q subgroup; responses in Z_q.
    for element in (commitment, t):
        if not is_group_element(element):
            return False
    if not (0 <= z1 < Q and 0 <= z2 < Q):
        return False

    c = _challenge(commitment, t, context, version)
    left = pow(G, z1, P) * pow(H, z2, P) % P
    right = t * pow(commitment, c, P) % P
    return secrets.compare_digest(format(left, "x"), format(right, "x"))
