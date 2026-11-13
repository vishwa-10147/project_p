"""
Measure EmpowerHer's performance for the project report.

    python manage.py run_benchmarks

Writes report/results/benchmarks.json (relative to the project root) and
prints a summary. Uses only synthetic data.
"""

import json
import os
import platform
import statistics
import time
from pathlib import Path

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.documents.ocr import extract_text
from apps.documents.validators import detect_type, extract_fields
from apps.funding.calculator import loan_summary
from apps.idea_vault import zkp
from apps.market.analysis import analyse
from apps.privacy.paillier import generate_keypair
from apps.schemes.recommender import recommend


def timed(func, repeat):
    """Median and min wall time of func() in milliseconds, and last result."""
    samples, result = [], None
    for _ in range(repeat):
        start = time.perf_counter()
        result = func()
        samples.append((time.perf_counter() - start) * 1000)
    return {
        "median_ms": round(statistics.median(samples), 3),
        "min_ms": round(min(samples), 3),
        "runs": repeat,
    }, result


class Command(BaseCommand):
    help = "Benchmark encryption, ZKP, OCR, recommendation and analysis."

    def handle(self, *args, **options):
        results = {
            "environment": {
                "python": platform.python_version(),
                "machine": platform.machine(),
                "system": f"{platform.system()} {platform.release()}",
            }
        }

        # --- Fernet at-rest encryption ----------------------------------
        fernet = Fernet(Fernet.generate_key())
        idea = ("Millet snack subscription boxes for offices. " * 23)[:1000]
        enc_stats, token = timed(lambda: fernet.encrypt(idea.encode()), 200)
        dec_stats, _ = timed(lambda: fernet.decrypt(token), 200)
        results["fernet"] = {
            "plaintext_bytes": len(idea.encode()),
            "ciphertext_bytes": len(token),
            "encrypt": enc_stats,
            "decrypt": dec_stats,
        }

        # --- Paillier homomorphic encryption ----------------------------
        keygen_stats, keys = timed(lambda: generate_keypair(2048), 5)
        public, private = keys
        enc_stats, c_income = timed(lambda: public.encrypt(60000), 20)
        c_exp = public.encrypt(35000)
        c_emi = public.encrypt(2000)
        compute_stats, c_result = timed(lambda: public.linear(
            [(c_income, 50), (c_exp, -50), (c_emi, -100)],
            constant=-100 * 9000,
        ), 20)
        dec_stats, value = timed(lambda: private.decrypt(c_result), 20)
        results["paillier"] = {
            "key_bits": 2048,
            "ciphertext_bits": c_income.bit_length(),
            "keygen": keygen_stats,
            "encrypt_one_value": enc_stats,
            "server_affordability_computation": compute_stats,
            "decrypt_one_value": dec_stats,
            "check": {"expected": 150000, "decrypted": value},
        }

        # --- Zero-knowledge proofs ---------------------------------------
        witness = os.urandom(32).hex()
        commit_stats, _ = timed(lambda: zkp.commit(idea, witness), 20)
        prove_stats, proof = timed(
            lambda: zkp.prove(idea, witness, "Benchmark verifier"), 20)
        verify_stats, ok = timed(lambda: zkp.verify(proof), 20)
        tampered = dict(proof, z2=format((int(proof["z2"], 16) + 1) % zkp.Q, "x"))
        results["zkp"] = {
            "group_bits": zkp.P.bit_length(),
            "proof_size_bytes": len(json.dumps(proof).encode()),
            "commit": commit_stats,
            "prove": prove_stats,
            "verify": verify_stats,
            "valid_proof_accepted": ok,
            "tampered_proof_rejected": not zkp.verify(tampered),
            "wrong_context_rejected": not zkp.verify(
                dict(proof, context="Someone else")),
        }

        # --- OCR on a synthetic PAN card ---------------------------------
        from apps.users.management.commands.seed_demo import synthetic_pan_card

        data = synthetic_pan_card().getvalue()
        extract_text(data, "image/png")  # warm up the model
        ocr_stats, (text, method, confidence) = timed(
            lambda: extract_text(data, "image/png"), 5)
        doc_type = detect_type(text)
        fields, checks = extract_fields(text, doc_type)
        results["ocr"] = {
            "image": "synthetic PAN card, 1000x560 px",
            "time": ocr_stats,
            "confidence": round(confidence, 4),
            "detected_type": doc_type,
            "masked_pan": fields.get("pan"),
            "checks_passed": all(c["passed"] for c in checks),
        }

        # --- Scheme recommendation and market analysis ------------------
        recommend(state="Telangana")  # warm up TF-IDF
        rec_stats, recs = timed(lambda: recommend(
            state="Telangana", category="food", stage="idea",
            social_groups=["shg"], amount_needed=300000,
            description="homemade pickles and millet snacks"), 50)
        results["recommender"] = {
            "schemes_in_dataset": 25,
            "time": rec_stats,
            "top_3": [
                {"id": r["scheme"]["id"], "score": r["score"]}
                for r in recs[:3]
            ],
        }

        analyse("Telangana", "food", district="Warangal")  # warm up
        market_stats, market = timed(
            lambda: analyse("Telangana", "food", district="Warangal"), 20)
        results["market"] = {
            "districts_in_dataset": 640,
            "time": market_stats,
            "example": {
                "district": market["matched_district"],
                "category": "food",
                "demand_index": market["demand_index"],
                "rank_in_state": market["rank_in_state"],
                "top_districts": market["top_districts_in_state"],
            },
            "all_categories_warangal": {
                category: analyse("Telangana", category,
                                  district="Warangal")["demand_index"]
                for category in ("food", "clothing", "beauty", "handicrafts",
                                 "agriculture", "education", "technology",
                                 "retail", "services")
            },
        }

        emi_stats, loan = timed(lambda: loan_summary(500000, 10, 36), 200)
        results["emi"] = {
            "example": {"principal": 500000, "rate": 10, "months": 36,
                        "emi": loan["emi"],
                        "total_interest": loan["total_interest"]},
            "time": emi_stats,
        }

        out_dir = Path(settings.BASE_DIR).parent.parent / "report" / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "benchmarks.json"
        out_file.write_text(json.dumps(results, indent=2, default=float))

        self.stdout.write(json.dumps(results, indent=2, default=float))
        self.stdout.write(self.style.SUCCESS(f"Saved {out_file}"))
