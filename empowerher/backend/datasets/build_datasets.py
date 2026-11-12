"""
Build the processed EmpowerHer datasets from the raw downloads.

Raw sources (datasets/raw/):
  - census.csv
      Census of India 2011, district level (640 districts).
      Mirror: github.com/nishusharma1608/India-Census-2011-Analysis
  - pib_women_msme_2024.pdf
      Ministry of MSME / PIB annexures (Feb 2024):
        I   State-wise women-owned MSMEs registered on Udyam + UAP
        II  State-wise CGTMSE guarantees approved for women
        III State-wise women beneficiaries under PMEGP

Outputs (datasets/processed/):
  - districts.csv      district-level demand indicators
  - states.csv         state-level indicators + women MSME ecosystem data

Run:  python datasets/build_datasets.py
"""

import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
OUT = HERE / "processed"

# Census 2011 predates Telangana (2014); these districts were in
# undivided Andhra Pradesh.
TELANGANA_2011_DISTRICTS = {
    "Adilabad", "Nizamabad", "Karimnagar", "Medak", "Hyderabad",
    "Rangareddy", "Mahbubnagar", "Nalgonda", "Warangal", "Khammam",
}

# Map every spelling seen in the sources to one canonical state name.
STATE_ALIASES = {
    "ORISSA": "Odisha",
    "PONDICHERRY": "Puducherry",
    "NCT OF DELHI": "Delhi",
    "JAMMU KASHMIR": "Jammu and Kashmir",
    "JAMMU & KASHMIR": "Jammu and Kashmir",
    "ANDAMAN & NICOBAR": "Andaman and Nicobar Islands",
    "ANDAMAN NICOBAR": "Andaman and Nicobar Islands",
    "CHANDIGARH-UT": "Chandigarh",
    "UTTAR PRADESH": "Uttar Pradesh",
    "TAMILNADU": "Tamil Nadu",
    "LAKSHADEEP": "Lakshadweep",
    "DADRA AND NAGAR HAVELI": "Dadra and Nagar Haveli and Daman and Diu",
    "DAMAN AND DIU": "Dadra and Nagar Haveli and Daman and Diu",
    "DADRA & NAGAR HAVELI AND DAMAN & DIU": (
        "Dadra and Nagar Haveli and Daman and Diu"
    ),
    "THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU": (
        "Dadra and Nagar Haveli and Daman and Diu"
    ),
}

SMALL_WORDS = {"and", "of"}


def canonical_state(name):
    key = re.sub(r"\s+", " ", str(name)).strip().upper()
    if key in STATE_ALIASES:
        return STATE_ALIASES[key]
    words = key.lower().split()
    return " ".join(
        w if w in SMALL_WORDS and i else w.capitalize()
        for i, w in enumerate(words)
    )


def to_number(text):
    return float(text.replace(",", ""))


# --------------------------------------------------------------------
# Census → district indicators
# --------------------------------------------------------------------

def build_districts():
    df = pd.read_csv(RAW / "census.csv")

    df = df.copy()
    df["state"] = df["State name"].map(canonical_state)
    df.loc[
        (df["state"] == "Andhra Pradesh")
        & df["District name"].isin(TELANGANA_2011_DISTRICTS),
        "state",
    ] = "Telangana"

    hh = df["Households"].clip(lower=1)
    pop = df["Population"].clip(lower=1)
    pp_total = df["Total_Power_Parity"].clip(lower=1)

    out = pd.DataFrame({
        "district_code": df["District code"],
        "state": df["state"],
        "district": df["District name"],
        "population": df["Population"],
        "female_population": df["Female"],
        "households": df["Households"],
        "urban_household_share": df["Urban_Households"] / hh,
        "female_literacy_rate": df["Female_Literate"] / df["Female"].clip(lower=1),
        "literacy_rate": df["Literate"] / pop,
        "female_worker_share": df["Female_Workers"] / df["Female"].clip(lower=1),
        "youth_share_0_29": df["Age_Group_0_29"] / pop,
        "internet_household_share": df["Households_with_Internet"] / hh,
        "computer_household_share": df["Households_with_Computer"] / hh,
        "mobile_household_share": (
            df["Households_with_Telephone_Mobile_Phone"] / hh
        ),
        "two_wheeler_household_share": (
            df["Households_with_Scooter_Motorcycle_Moped"] / hh
        ),
        "tv_household_share": df["Households_with_Television"] / hh,
        "agri_worker_share": (
            (df["Cultivator_Workers"] + df["Agricultural_Workers"])
            / df["Workers"].clip(lower=1)
        ),
        "household_industry_worker_share": (
            df["Household_Workers"] / df["Workers"].clip(lower=1)
        ),
        "graduate_share": df["Graduate_Education"] / pop,
        # Share of households in the top purchasing-power bands (> Rs 3.3 lakh).
        "high_income_household_share": (
            (df["Power_Parity_Rs_330000_545000"]
             + df["Power_Parity_Above_Rs_545000"]) / pp_total
        ),
    })

    numeric = out.select_dtypes("float").columns
    out[numeric] = out[numeric].round(4)
    out["district"] = out["district"].str.strip()
    return out.sort_values(["state", "district"])


# --------------------------------------------------------------------
# PIB PDF → state women-entrepreneurship ecosystem
# --------------------------------------------------------------------

ROW = re.compile(
    r"(?:^|\s)\d{1,2}\s+([A-Za-z][A-Za-z &\-\.\n]*?)\s+"
    r"([\d,]+(?:\.\d+)?)\s+([\d,]+(?:\.\d+)?)(?:\s+([\d,]+(?:\.\d+)?))?"
    r"(?=\s+\d{1,2}\s+[A-Za-z]|\s+Total|\s*$)",
    re.S | re.I,
)


def parse_annexure(text):
    rows = {}
    for match in ROW.finditer(text):
        name = canonical_state(match.group(1).replace("\n", " "))
        values = [to_number(v) for v in match.groups()[1:] if v]
        rows[name] = values
    return rows


def build_states(districts):
    text = "\n".join(
        page.extract_text() for page in PdfReader(
            RAW / "pib_women_msme_2024.pdf"
        ).pages
    )
    text = text.replace("*", "")

    def table(start, end=None):
        body = text.split(start, 1)[1]
        if end:
            body = body.split(end, 1)[0]
        # Drop the header row, then cut at the totals row.
        body = body.split("\n1 ", 1)[1]
        return "1 " + re.split(r"\bTotal\b", body, flags=re.I)[0]

    msme = parse_annexure(table("Since Inception", "Annexure –II"))
    cgtmse = parse_annexure(table("Annexure –II", "Annexure –III"))
    pmegp = parse_annexure(table("Annexure –III"))

    agg = districts.assign(
        literate_f=districts.female_literacy_rate * districts.female_population,
        urban_hh=districts.urban_household_share * districts.households,
        internet_hh=districts.internet_household_share * districts.households,
    ).groupby("state").agg(
        population=("population", "sum"),
        female_population=("female_population", "sum"),
        households=("households", "sum"),
        literate_f=("literate_f", "sum"),
        urban_hh=("urban_hh", "sum"),
        internet_hh=("internet_hh", "sum"),
        districts=("district", "count"),
    )

    agg["female_literacy_rate"] = (
        agg.literate_f / agg.female_population
    ).round(4)
    agg["urban_household_share"] = (agg.urban_hh / agg.households).round(4)
    agg["internet_household_share"] = (
        agg.internet_hh / agg.households
    ).round(4)
    agg = agg.drop(columns=["literate_f", "urban_hh", "internet_hh"])

    states = agg.reset_index()
    names = set(states.state) | set(msme) | set(cgtmse) | set(pmegp)
    states = states.set_index("state").reindex(sorted(names))

    states["women_msmes_udyam"] = [msme.get(s, [None])[0] for s in states.index]
    states["women_msmes_uap"] = [
        (msme.get(s) or [None, None])[1] for s in states.index
    ]
    states["women_msmes_total"] = [
        (msme.get(s) or [None, None, None])[-1] for s in states.index
    ]
    states["cgtmse_women_guarantees"] = [
        (cgtmse.get(s) or [None])[0] for s in states.index
    ]
    states["cgtmse_women_amount_cr"] = [
        (cgtmse.get(s) or [None, None])[1] for s in states.index
    ]
    states["pmegp_women_projects"] = [
        (pmegp.get(s) or [None])[0] for s in states.index
    ]
    states["pmegp_women_margin_money_cr"] = [
        (pmegp.get(s) or [None, None])[1] for s in states.index
    ]
    states["women_msmes_per_1000_women"] = (
        states.women_msmes_total / states.female_population * 1000
    ).round(2)

    return states.reset_index().rename(columns={"index": "state"})


def main():
    OUT.mkdir(exist_ok=True)
    districts = build_districts()
    states = build_states(districts)

    districts.to_csv(OUT / "districts.csv", index=False)
    states.to_csv(OUT / "states.csv", index=False)

    print(f"districts.csv: {len(districts)} rows")
    print(f"states.csv:    {len(states)} rows")
    missing = states[states.women_msmes_total.isna()].state.tolist()
    if missing:
        print("States without MSME data:", missing)


if __name__ == "__main__":
    main()
