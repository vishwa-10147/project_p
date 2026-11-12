from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from config.testing import make_client
from idea_vault import zkp


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
