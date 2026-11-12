"""
Read-only access to the EmpowerHer datasets in backend/datasets/.

Curated JSON lives in datasets/curated/, processed CSVs (built by
datasets/build_datasets.py from the raw downloads) in datasets/processed/.
Files are loaded once per process and cached.
"""

import json
from functools import lru_cache

import pandas as pd
from django.conf import settings


@lru_cache(maxsize=None)
def load_json(name):
    path = settings.DATASETS_DIR / "curated" / f"{name}.json"
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=None)
def load_csv(name):
    path = settings.DATASETS_DIR / "processed" / f"{name}.csv"
    return pd.read_csv(path)


def normalise(text):
    """Lower-case and collapse whitespace for loose comparisons."""
    return " ".join(str(text or "").lower().replace("&", "and").split())


def match_state(name):
    """Return the canonical state name from the datasets, or None."""
    wanted = normalise(name)
    if not wanted:
        return None

    aliases = {
        "orissa": "odisha",
        "pondicherry": "puducherry",
        "tamilnadu": "tamil nadu",
        "j and k": "jammu and kashmir",
        "nct of delhi": "delhi",
        "new delhi": "delhi",
        "ap": "andhra pradesh",
        "ts": "telangana",
        "tg": "telangana",
    }
    wanted = aliases.get(wanted, wanted)

    for state in load_csv("states")["state"]:
        if normalise(state) == wanted:
            return state
    return None
