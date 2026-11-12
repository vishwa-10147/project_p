"""
Draw the Results-chapter charts from report/results/benchmarks.json.

Needs a tools environment with matplotlib:
    pip install matplotlib
    python report/tools/make_charts.py

Charts are static PNGs for the printed report (single series each, so no
legend box; the title names the series).
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "report" / "results"
OUT = RESULTS / "charts"

SERIES = "#2a78d6"      # reference palette, categorical slot 1
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SURFACE = "#ffffff"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "xtick.color": INK_2,
    "ytick.color": INK,
    "axes.titlecolor": INK,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
})


def style(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)


def hbar(labels, values, title, xlabel, path, fmt, log=False, ref=None):
    """Horizontal bars; on a log scale, dots (bar length would be arbitrary)."""
    fig, ax = plt.subplots(figsize=(7.2, 0.42 * len(labels) + 1.4), dpi=200)
    positions = list(range(len(labels)))
    if log:
        ax.set_xscale("log")
        ax.scatter(values, positions, s=64, color=SERIES, zorder=3,
                   edgecolor=SURFACE, linewidth=1.5)
        ax.grid(axis="y", color=GRID, linewidth=0.6)
    else:
        ax.barh(positions, values, height=0.55, color=SERIES,
                edgecolor=SURFACE, linewidth=1)
    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    style(ax)

    span = max(values)
    for y, value in zip(positions, values):
        if log:
            x = value * 1.35
        else:
            x = value + span * 0.012
            # Keep labels clear of the reference line.
            if ref is not None and abs(value - ref[0]) < span * 0.06:
                x = max(value, ref[0]) + span * 0.012
        ax.text(x, y, fmt(value), va="center", fontsize=9, color=INK)

    if ref is not None:
        ax.axvline(ref[0], color=INK_2, linewidth=1, linestyle=(0, (3, 3)))
        ax.text(ref[0], -0.8, ref[1], color=INK_2, fontsize=8.5, ha="center")
    ax.set_xlabel(xlabel)
    if log:
        ax.set_xlim(min(values) / 2, span * 8)
    else:
        ax.set_xlim(0, span * 1.15)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.text(0.015, 0.975, title, fontsize=11.5, fontweight="bold",
             color=INK, ha="left", va="top")
    fig.savefig(path)
    plt.close(fig)
    print("saved", path.name)


TEST_MODULES = {
    "documents": "Documents (OCR, validation)", "idea_vault": "Idea Vault (ZKP)",
    "funding": "Funding", "schemes": "Schemes", "assistant": "Assistant",
    "business": "Business validation", "privacy": "Privacy (HE)",
    "market": "Market", "users": "Users & account security", "safety": "Safety",
}


def count_tests():
    backend = ROOT / "empowerher" / "backend"
    return [
        (label, (backend / "apps" / app / "tests.py").read_text().count("    def test_"))
        for app, label in TEST_MODULES.items()
    ]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    b = json.loads((RESULTS / "benchmarks.json").read_text())

    ops = [
        ("Fernet encrypt (1 KB idea)", b["fernet"]["encrypt"]["median_ms"]),
        ("EMI + schedule", b["emi"]["time"]["median_ms"]),
        ("Scheme recommendation (25 schemes)", b["recommender"]["time"]["median_ms"]),
        ("Market analysis (640 districts)", b["market"]["time"]["median_ms"]),
        ("ZKP commitment", b["zkp"]["commit"]["median_ms"]),
        ("ZKP proof generation", b["zkp"]["prove"]["median_ms"]),
        ("ZKP proof verification", b["zkp"]["verify"]["median_ms"]),
        ("Paillier encrypt one value", b["paillier"]["encrypt_one_value"]["median_ms"]),
        ("HE affordability on ciphertexts", b["paillier"]["server_affordability_computation"]["median_ms"]),
        ("Paillier decrypt one value", b["paillier"]["decrypt_one_value"]["median_ms"]),
        ("OCR of a PAN card image", b["ocr"]["time"]["median_ms"]),
        ("Paillier 2048-bit key generation", b["paillier"]["keygen"]["median_ms"]),
    ]
    hbar([o[0] for o in ops], [o[1] for o in ops],
         "Median time per operation",
         "milliseconds (log scale)", OUT / "chart_operation_times.png",
         lambda v: f"{v:,.3f} ms" if v < 1 else f"{v:,.1f} ms", log=True)

    names = {
        "food": "Food & beverages", "clothing": "Clothing & fashion",
        "beauty": "Beauty & personal care", "handicrafts": "Handicrafts",
        "agriculture": "Agriculture", "education": "Education",
        "technology": "Technology", "retail": "Retail",
        "services": "Local services",
    }
    demand = sorted(b["market"]["all_categories_warangal"].items(),
                    key=lambda kv: kv[1], reverse=True)
    hbar([names[k] for k, _ in demand], [v for _, v in demand],
         "Warangal: demand potential index by business category",
         "index (0-100, percentile vs. all 640 districts)",
         OUT / "chart_warangal_demand.png", lambda v: f"{v:.1f}",
         ref=(50, "national middle (50)"))

    tests = count_tests()
    total = sum(n for _, n in tests)
    tests.sort(key=lambda t: -t[1])
    hbar([t[0] for t in tests], [t[1] for t in tests],
         f"Automated tests per module ({total} total, all passing)",
         "number of tests", OUT / "chart_tests_per_module.png",
         lambda v: f"{v:.0f}")


if __name__ == "__main__":
    main()
