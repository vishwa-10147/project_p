"""
Local market demand indicators from Census 2011 and Ministry of MSME data.

For each business category we combine census indicators that act as
demand proxies (e.g. internet access for technology, female literacy
and urbanisation for beauty services). Each indicator is converted to a
percentile across all 640 districts, then weighted into a 0-100
"demand potential index". This is a relative comparison between
districts, not a market-size forecast.
"""

import difflib
import math
from functools import lru_cache

from config.datasets import load_csv, match_state, normalise

INDICATOR_LABELS = {
    "population": "Population",
    "households": "Number of households",
    "urban_household_share": "Urban households",
    "rural_household_share": "Rural households",
    "female_literacy_rate": "Female literacy",
    "literacy_rate": "Literacy",
    "female_worker_share": "Working women",
    "youth_share_0_29": "Population under 30",
    "internet_household_share": "Households with internet",
    "computer_household_share": "Households with a computer",
    "mobile_household_share": "Households with a phone",
    "two_wheeler_household_share": "Households with a two-wheeler",
    "tv_household_share": "Households with a TV",
    "agri_worker_share": "Agricultural workforce",
    "household_industry_worker_share": "Household-industry workers",
    "graduate_share": "Graduates",
    "high_income_household_share": "Higher-income households",
}

# Category -> {indicator: weight}. Weights sum to 1.
CATEGORY_MODELS = {
    "food": {
        "population": 0.3, "urban_household_share": 0.25,
        "female_worker_share": 0.15, "high_income_household_share": 0.15,
        "two_wheeler_household_share": 0.15,
    },
    "clothing": {
        "population": 0.25, "high_income_household_share": 0.25,
        "urban_household_share": 0.2, "tv_household_share": 0.15,
        "female_literacy_rate": 0.15,
    },
    "beauty": {
        "urban_household_share": 0.3, "female_literacy_rate": 0.2,
        "high_income_household_share": 0.25, "female_worker_share": 0.1,
        "youth_share_0_29": 0.15,
    },
    "handicrafts": {
        "household_industry_worker_share": 0.35,
        "high_income_household_share": 0.2, "internet_household_share": 0.2,
        "population": 0.1, "female_worker_share": 0.15,
    },
    "agriculture": {
        "agri_worker_share": 0.4, "rural_household_share": 0.25,
        "population": 0.2, "mobile_household_share": 0.15,
    },
    "education": {
        "youth_share_0_29": 0.3, "literacy_rate": 0.2,
        "graduate_share": 0.15, "internet_household_share": 0.15,
        "population": 0.2,
    },
    "technology": {
        "internet_household_share": 0.3, "computer_household_share": 0.25,
        "graduate_share": 0.2, "urban_household_share": 0.15,
        "high_income_household_share": 0.1,
    },
    "retail": {
        "population": 0.3, "households": 0.2,
        "two_wheeler_household_share": 0.15, "mobile_household_share": 0.15,
        "urban_household_share": 0.2,
    },
    "services": {
        "urban_household_share": 0.3, "high_income_household_share": 0.2,
        "graduate_share": 0.15, "mobile_household_share": 0.15,
        "population": 0.2,
    },
    "other": {
        "population": 0.35, "urban_household_share": 0.25,
        "mobile_household_share": 0.2, "high_income_household_share": 0.2,
    },
}

SOURCES = [
    {
        "name": "Census of India 2011 (district tables)",
        "url": "https://censusindia.gov.in/",
    },
    {
        "name": "Ministry of MSME annexure on women-owned MSMEs, "
                "CGTMSE and PMEGP (PIB, Feb 2024)",
        "url": "https://static.pib.gov.in/WriteReadData/specificdocs/"
               "documents/2024/feb/doc202428308701.pdf",
    },
]


@lru_cache(maxsize=1)
def district_table():
    df = load_csv("districts").copy()
    df["rural_household_share"] = 1 - df["urban_household_share"]
    # Percentile rank of every indicator across all districts.
    for column in INDICATOR_LABELS:
        df[f"pct_{column}"] = df[column].rank(pct=True) * 100
    return df


def list_states():
    states = load_csv("states")
    return states["state"].tolist()


def list_districts(state):
    canonical = match_state(state)
    if not canonical:
        return []
    df = district_table()
    return sorted(df.loc[df.state == canonical, "district"].tolist())


def find_district(state, location):
    """Fuzzy-match a free-text location to a census district."""
    canonical = match_state(state)
    if not canonical or not normalise(location):
        return None
    df = district_table()
    candidates = df.loc[df.state == canonical, "district"].tolist()
    lookup = {normalise(name): name for name in candidates}
    wanted = normalise(location).split(",")[0].strip()
    if wanted in lookup:
        return lookup[wanted]
    # Treat names like "Rangareddy" vs "Ranga Reddy" alike.
    squashed = {k.replace(" ", ""): v for k, v in lookup.items()}
    if wanted.replace(" ", "") in squashed:
        return squashed[wanted.replace(" ", "")]
    close = difflib.get_close_matches(wanted, list(lookup), n=1, cutoff=0.8)
    return lookup[close[0]] if close else None


def _score_row(row, model):
    return sum(row[f"pct_{name}"] * weight for name, weight in model.items())


def _band(score):
    if score >= 75:
        return "High"
    if score >= 50:
        return "Above average"
    if score >= 25:
        return "Below average"
    return "Low"


def state_ecosystem(canonical_state):
    states = load_csv("states")
    row = states.loc[states.state == canonical_state]
    if row.empty:
        return None
    row = row.iloc[0]
    national = (
        states.women_msmes_total.sum() / states.female_population.sum() * 1000
    )

    def clean(value):
        return None if value is None or (
            isinstance(value, float) and math.isnan(value)
        ) else value

    density = clean(row.women_msmes_per_1000_women)
    return {
        "state": canonical_state,
        "women_owned_msmes": clean(row.women_msmes_total),
        "women_msmes_per_1000_women": density,
        "national_women_msmes_per_1000_women": round(national, 2),
        "cgtmse_guarantees_for_women": clean(row.cgtmse_women_guarantees),
        "cgtmse_amount_crore": clean(row.cgtmse_women_amount_cr),
        "pmegp_women_projects": clean(row.pmegp_women_projects),
        "pmegp_margin_money_crore": clean(row.pmegp_women_margin_money_cr),
        "interpretation": (
            None if density is None else (
                "More women-owned enterprises per capita than the national "
                "average: a stronger support ecosystem, but also more "
                "competition. Differentiate your offer."
                if density >= national else
                "Fewer women-owned enterprises per capita than the national "
                "average: less competition from similar businesses, but "
                "you may need to build awareness and networks."
            )
        ),
    }


def analyse(state, category, district=None, location=None):
    canonical = match_state(state)
    if not canonical:
        return {"error": "State not recognised."}
    if category not in CATEGORY_MODELS:
        return {"error": "Unknown business category."}

    model = CATEGORY_MODELS[category]
    df = district_table()
    df = df.assign(score=df.apply(_score_row, axis=1, model=model))
    in_state = df[df.state == canonical]

    matched = None
    if district:
        matched = find_district(canonical, district)
    if not matched and location:
        matched = find_district(canonical, location)

    result = {
        "state": canonical,
        "category": category,
        "matched_district": matched,
        "method": (
            "Each indicator is ranked against all 640 districts "
            "(percentile 0-100) and combined with category weights. "
            "Scores compare districts with each other; they do not "
            "measure sales or market size."
        ),
        "data_year_note": (
            "Census indicators are from 2011, the latest district-level "
            "census. Districts created after 2011 are shown under their "
            "parent district. Use them as relative signals and confirm "
            "with local customer research."
        ),
        "ecosystem": state_ecosystem(canonical),
        "top_districts_in_state": [
            {"district": r.district, "score": round(r.score, 1)}
            for r in in_state.nlargest(5, "score").itertuples()
        ],
        "sources": SOURCES,
    }

    if in_state.empty:
        result["note"] = "No census district data for this state/UT."
        return result

    state_score = in_state.score.mean()
    result["state_average_score"] = round(state_score, 1)

    if matched:
        row = in_state[in_state.district == matched].iloc[0]
        score = row.score
        rank = int((in_state.score > score).sum()) + 1
        indicators = [
            {
                "indicator": INDICATOR_LABELS[name],
                "weight": weight,
                "value": round(float(row[name]), 4),
                "national_percentile": round(float(row[f"pct_{name}"]), 1),
            }
            for name, weight in model.items()
        ]
        strengths = [i["indicator"] for i in indicators
                     if i["national_percentile"] >= 70]
        weaknesses = [i["indicator"] for i in indicators
                      if i["national_percentile"] < 35]
        result.update({
            "demand_index": round(score, 1),
            "demand_band": _band(score),
            "rank_in_state": rank,
            "districts_in_state": len(in_state),
            "population_2011": int(row.population),
            "households_2011": int(row.households),
            "indicators": indicators,
            "insights": _insights(strengths, weaknesses, rank,
                                  len(in_state), matched),
        })
    else:
        result.update({
            "demand_index": round(state_score, 1),
            "demand_band": _band(state_score),
            "note": (
                "District not matched; showing the state average. "
                "Choose a district for a local view."
            ),
            "insights": [],
        })
    return result


def _insights(strengths, weaknesses, rank, total, district):
    insights = []
    if strengths:
        insights.append(
            f"{district} ranks highly nationally on: "
            + ", ".join(strengths) + "."
        )
    if weaknesses:
        insights.append(
            "Weaker demand signals: " + ", ".join(weaknesses)
            + ". Consider online sales or nearby towns to widen reach."
        )
    if rank <= max(1, total // 4):
        insights.append(
            f"One of the strongest districts in the state for this "
            f"category (rank {rank} of {total})."
        )
    elif rank > total * 3 // 4:
        insights.append(
            f"Ranks {rank} of {total} in the state; validate demand "
            f"carefully with a small pilot before investing heavily."
        )
    return insights
