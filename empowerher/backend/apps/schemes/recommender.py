"""
Government-scheme recommendation engine.

Combines transparent eligibility rules (state, business stage, social
group, amount needed) with TF-IDF text similarity between the user's
business description and each scheme's summary and keywords.
Every score comes with human-readable reasons so users can see why a
scheme was suggested.
"""

from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config.datasets import load_json, match_state, normalise

SOCIAL_GROUP_LABELS = {
    "sc_st": "SC/ST entrepreneurs",
    "obc": "backward classes",
    "minority": "minority communities",
    "rural": "rural entrepreneurs",
    "shg": "Self-Help Group members",
    "artisan": "traditional artisans",
    "street_vendor": "street vendors",
}

STAGES = {"idea", "startup", "existing", "expansion"}


def all_schemes():
    return load_json("schemes")["schemes"]


def get_scheme(scheme_id):
    return next((s for s in all_schemes() if s["id"] == scheme_id), None)


def scheme_text(scheme):
    return " ".join([
        scheme["name"],
        scheme["summary"],
        scheme.get("keywords", ""),
        " ".join(scheme.get("eligibility", [])),
    ])


@lru_cache(maxsize=1)
def _vectoriser():
    schemes = all_schemes()
    vectoriser = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    matrix = vectoriser.fit_transform([scheme_text(s) for s in schemes])
    return vectoriser, matrix


def text_similarity(description):
    """Return a cosine similarity for every scheme (same order)."""
    if not normalise(description):
        return [0.0] * len(all_schemes())
    vectoriser, matrix = _vectoriser()
    query = vectoriser.transform([description])
    return cosine_similarity(query, matrix)[0].tolist()


def filter_schemes(state=None, category=None, stage=None,
                   benefit_type=None, query=None):
    """Plain filtering for the browse view."""
    canonical = match_state(state) if state else None
    results = []

    for scheme in all_schemes():
        if state and "ALL" not in scheme["states"] and (
            canonical not in scheme["states"]
        ):
            continue
        if category and "any" not in scheme["categories"] and (
            category not in scheme["categories"]
        ):
            continue
        if stage and stage not in scheme["stages"]:
            continue
        if benefit_type and benefit_type not in scheme["benefit_type"]:
            continue
        if query:
            haystack = normalise(scheme_text(scheme))
            if not all(word in haystack for word in normalise(query).split()):
                continue
        results.append(scheme)

    return results


def recommend(state=None, category=None, stage=None, social_groups=None,
              amount_needed=None, description="", limit=8):
    """
    Score every scheme for an entrepreneur and return the best matches.

    Hard rules exclude schemes that cannot apply (wrong state, wrong
    business stage, or reserved for a social group the user is not in).
    Soft rules add points and explain the match.
    """
    social_groups = set(social_groups or [])
    canonical_state = match_state(state) if state else None
    similarities = text_similarity(description)
    recommendations = []

    for scheme, similarity in zip(all_schemes(), similarities, strict=True):
        reasons = []
        cautions = []
        score = 0.0

        # --- Hard eligibility rules -----------------------------------
        if "ALL" in scheme["states"]:
            reasons.append("Available across India")
        elif canonical_state in scheme["states"]:
            score += 20
            reasons.append(f"State scheme for {canonical_state}")
        else:
            continue

        if stage and stage in STAGES:
            if stage not in scheme["stages"]:
                continue
            score += 10
            reasons.append(f"Suits the '{stage}' business stage")

        required_groups = set(scheme.get("social_groups", []))
        # Schemes for SHGs/rural/artisans/vendors are open to those
        # groups; schemes for caste or community groups require
        # membership.
        strict_groups = required_groups & {"sc_st", "obc", "minority",
                                           "artisan", "street_vendor"}
        if strict_groups and not (strict_groups & social_groups):
            continue

        # --- Soft scoring ---------------------------------------------
        matched_groups = required_groups & social_groups
        if matched_groups:
            score += 15
            reasons.append(
                "Targets " + ", ".join(
                    SOCIAL_GROUP_LABELS[g] for g in sorted(matched_groups)
                )
            )
        elif required_groups:
            score -= 5
            cautions.append(
                "Mainly for " + ", ".join(
                    SOCIAL_GROUP_LABELS[g] for g in sorted(required_groups)
                )
            )

        if category:
            if category in scheme["categories"]:
                score += 20
                reasons.append("Designed for your business category")
            elif "any" in scheme["categories"]:
                score += 8
            else:
                score -= 10
                cautions.append("Focused on other business categories")

        if scheme.get("women_specific"):
            score += 10
            reasons.append("Specifically for women entrepreneurs")

        max_amount = scheme.get("max_amount_inr")
        min_amount = scheme.get("min_amount_inr")
        if amount_needed:
            if max_amount and amount_needed > max_amount:
                score -= 8
                cautions.append(
                    f"Support is capped at Rs {max_amount:,}; "
                    "you may need to combine sources"
                )
            elif min_amount and amount_needed < min_amount:
                score -= 8
                cautions.append(
                    f"Minimum support is Rs {min_amount:,}"
                )
            elif max_amount:
                score += 10
                reasons.append("Covers the amount you need")

        if similarity > 0.05:
            score += round(similarity * 60, 1)
            reasons.append("Matches words in your business description")

        if scheme.get("status") == "check_status":
            # Validity ended or continuation pending: ranked by relevance as
            # usual, but clearly flagged so nobody applies blind.
            cautions.append(
                "Check this scheme's current status before applying: "
                + scheme.get("status_note", "")
            )

        recommendations.append({
            "scheme": scheme,
            "score": round(score, 1),
            "text_similarity": round(similarity, 3),
            "reasons": reasons,
            "cautions": cautions,
        })

    recommendations.sort(key=lambda item: item["score"], reverse=True)
    return recommendations[:limit]
