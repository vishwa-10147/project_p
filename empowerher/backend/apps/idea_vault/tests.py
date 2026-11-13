import json

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from apps.idea_vault import zkp
from apps.idea_vault.models import ConfidentialIdea
from config.testing import make_client


class ZkpTests(SimpleTestCase):
    witness = "ab" * 32

    def test_valid_proof_verifies(self):
        self.assertTrue(zkp.verify(zkp.prove("idea", self.witness, "ctx")))

    def test_proof_is_bound_to_context(self):
        proof = zkp.prove("idea", self.witness, "investor A")
        self.assertFalse(zkp.verify(dict(proof, context="investor B")))

    def test_tampered_proof_fails(self):
        proof = zkp.prove("idea", self.witness, "ctx")
        z1 = format((int(proof["z1"], 16) + 1) % zkp.Q, "x")
        self.assertFalse(zkp.verify(dict(proof, z1=z1)))
        self.assertFalse(zkp.verify({"commitment": "zz"}))

    def test_commitment_hides_and_binds(self):
        self.assertNotEqual(zkp.commit("idea", "00" * 32),
                            zkp.commit("idea", "01" * 32))
        self.assertNotEqual(zkp.commit("idea A", self.witness),
                            zkp.commit("idea B", self.witness))


class VaultFlowTests(TestCase):
    def test_register_prove_and_verify(self):
        _, client = make_client()
        created = client.post("/api/ideas/", {
            "title": "Snacks", "idea": "Millet snack boxes",
        }, format="json").data
        self.assertTrue(created["pedersen_commitment"])

        proof = client.post(f"/api/ideas/{created['id']}/proof/", {
            "witness_secret": created["witness_secret"],
            "context": "For mentor review",
        }, format="json")
        self.assertEqual(proof.status_code, 200, proof.data)

        verified = APIClient().post("/api/ideas/verify-proof/",
                                    {"proof": proof.data["proof"]},
                                    format="json")
        self.assertTrue(verified.data["valid_proof"])
        self.assertTrue(verified.data["registered_on_empowerher"])
        self.assertNotIn("Millet", str(verified.data))

    def test_wrong_witness_is_rejected(self):
        _, client = make_client()
        created = client.post("/api/ideas/", {
            "title": "Snacks", "idea": "Millet snack boxes",
        }, format="json").data
        response = client.post(f"/api/ideas/{created['id']}/proof/", {
            "witness_secret": "00" * 32, "context": "x",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_owner_isolation(self):
        _, owner = make_client()
        created = owner.post("/api/ideas/", {
            "title": "Snacks", "idea": "Secret",
        }, format="json").data
        _, other = make_client(username="other")
        self.assertEqual(
            other.get(f"/api/ideas/{created['id']}/").status_code, 404)


def browser_vault(passphrase="correct horse battery", iterations=100_000):
    """Do in Python what vault-crypto.js does in the browser."""
    import base64
    import json
    import os

    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    salt = os.urandom(16)
    key = PBKDF2HMAC(hashes.SHA256(), 32, salt, iterations).derive(passphrase.encode())

    def seal(text):
        iv = os.urandom(12)
        ct = AESGCM(key).encrypt(iv, text.encode(), None)
        return {"v": 1, "alg": "AES-256-GCM",
                "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode()}

    def open_(envelope):
        return AESGCM(key).decrypt(base64.b64decode(envelope["iv"]),
                                   base64.b64decode(envelope["ct"]), None).decode()

    settings = {"salt": base64.b64encode(salt).decode(), "iterations": iterations,
                "key_check": seal("EmpowerHer vault key check v1")}

    def seal_idea(idea, witness="cd" * 32):
        return {
            "encrypted_payload": seal(json.dumps({"idea": idea, "witness": witness})),
            "pedersen_commitment": format(zkp.commit(idea, witness, version=2), "x"),
        }

    return settings, seal_idea, open_


class EndToEndVaultTests(TestCase):
    IDEA = "Solar-powered millet processing unit for SHGs"

    def setUp(self):
        self.user, self.client = make_client()
        self.settings, self.seal_idea, self.open = browser_vault()

    def setup_key(self):
        response = self.client.post("/api/ideas/key/", self.settings, format="json")
        self.assertEqual(response.status_code, 201, response.data)

    def register(self, idea=IDEA, witness="cd" * 32):
        return self.client.post("/api/ideas/", {
            "title": "Millet unit", **self.seal_idea(idea, witness)}, format="json")

    def test_key_settings_round_trip(self):
        self.assertFalse(self.client.get("/api/ideas/key/").data["configured"])
        self.setup_key()
        data = self.client.get("/api/ideas/key/").data
        self.assertTrue(data["configured"])
        self.assertEqual(data["salt"], self.settings["salt"])
        self.assertEqual(self.open(data["key_check"]), "EmpowerHer vault key check v1")

    def test_key_settings_are_validated(self):
        for bad in ({**self.settings, "iterations": 10},
                    {**self.settings, "salt": "c2hvcnQ="},
                    {**self.settings, "key_check": {"v": 9}}):
            with self.subTest(bad=bad):
                response = self.client.post("/api/ideas/key/", bad, format="json")
                self.assertEqual(response.status_code, 400)

    def test_needs_a_vault_key_first(self):
        self.assertEqual(self.register().status_code, 400)

    def test_server_stores_only_ciphertext(self):
        self.setup_key()
        created = self.register()
        self.assertEqual(created.status_code, 201, created.data)
        item = ConfidentialIdea.objects.get(pk=created.data["id"])
        self.assertEqual(item.encryption, "browser")
        self.assertNotIn("millet", item.encrypted_idea.lower())
        self.assertNotIn("cd" * 32, item.encrypted_idea)

        detail = self.client.get(f"/api/ideas/{item.pk}/").data
        self.assertNotIn("idea", detail)
        opened = json.loads(self.open(detail["encrypted_payload"]))
        self.assertEqual(opened["idea"], self.IDEA)

    def test_browser_proof_verifies_publicly(self):
        self.setup_key()
        created = self.register().data
        proof = zkp.prove(self.IDEA, "cd" * 32, "For ABC Angels", version=2)
        self.assertEqual(proof["commitment"], created["pedersen_commitment"])
        result = APIClient().post("/api/ideas/verify-proof/", {"proof": proof},
                                  format="json").data
        self.assertTrue(result["valid_proof"])
        self.assertTrue(result["registered_on_empowerher"])

    def test_server_refuses_to_prove_end_to_end_ideas(self):
        self.setup_key()
        created = self.register().data
        response = self.client.post(f"/api/ideas/{created['id']}/proof/", {
            "witness_secret": "cd" * 32, "context": "x"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("browser", response.data["error"])

    def test_invalid_commitment_or_payload_rejected(self):
        self.setup_key()
        sealed = self.seal_idea(self.IDEA)
        for bad in ({**sealed, "pedersen_commitment": "1"},
                    {**sealed, "pedersen_commitment": "zz"},
                    {**sealed, "encrypted_payload": {"v": 1, "alg": "AES-256-GCM",
                                                     "iv": "AAAA", "ct": "AAAA"}}):
            with self.subTest(bad=bad):
                response = self.client.post("/api/ideas/", {"title": "t", **bad},
                                            format="json")
                self.assertEqual(response.status_code, 400)

    def test_duplicate_commitment_rejected(self):
        self.setup_key()
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.register().status_code, 400)

    def test_passphrase_cannot_be_replaced_while_ideas_use_it(self):
        self.setup_key()
        self.register()
        other, _, _ = browser_vault("a different passphrase")
        response = self.client.post("/api/ideas/key/", other, format="json")
        self.assertEqual(response.status_code, 409)

    def test_other_users_cannot_read_end_to_end_ideas(self):
        self.setup_key()
        created = self.register().data
        _, other = make_client(username="someone")
        self.assertEqual(other.get(f"/api/ideas/{created['id']}/").status_code, 404)

    def test_export_contains_ciphertext_not_plaintext(self):
        self.setup_key()
        self.register()
        exported = self.client.get("/api/users/export/").data
        entry = exported["idea_vault"][0]
        self.assertEqual(entry["encryption"], "browser")
        self.assertIsNone(entry["idea"])
        self.assertIn("ct", entry["encrypted_payload"])
