"""Static charts for docs/ and the one-page PDF, drawn from the committed caches."""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent.parent / ".venv" / ".mpl"))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import stats  # noqa: E402

INK = "#17202a"
MUTED = "#55606e"
GRID = "#d8dee6"
TEAL = ["#b8dfe3", "#4ea8b2", "#0b6e79"]  # one hue, light to dark
ACCENT = "#8a5300"



def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def load_numeric(data: Path) -> list[dict]:
    with open(data / "hospitals.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        try:
            r["m"] = float(r["op18b"])
        except ValueError:
            continue
        out.append(r)
    return out


def chart_distribution(data: Path, out: Path) -> Path:
    rows = load_numeric(data)
    ref = json.loads((data / "reference.json").read_text(encoding="utf-8"))
    vals = [r["m"] for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=160)
    bins = list(range(0, 481, 10))
    ax.hist([min(v, 479) for v in vals], bins=bins, color=TEAL[1], edgecolor="white", linewidth=0.6)
    nat = float(ref["national"]["OP_18b"]["score"])
    med = ref["summary"]["op18b_hospital_quantiles"]["p50"]
    top = ax.get_ylim()[1]
    for x, lab, dy in ((med, f"median hospital {med:.0f} min", 0.95), (nat, f"CMS national {nat:.0f} min", 0.82)):
        ax.axvline(x, color=INK, linewidth=1.2, linestyle="--" if x == nat else "-")
        ax.text(x + 4, top * dy, lab, color=INK, fontsize=8.5)
    p = ref["summary"]["periods"]["OP_18b"]
    ax.set_title(f"Median ED visit time (OP-18b) across {len(vals):,} US hospitals, {p['start']}–{p['end']}",
                 fontsize=10, color=INK, loc="left")
    ax.set_xlabel("minutes from arrival to departure, discharged patients (480+ shown at 480)", fontsize=9, color=MUTED)
    ax.set_ylabel("hospitals", fontsize=9, color=MUTED)
    ax.set_xticks(range(0, 481, 60))
    _style(ax)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def chart_assumed_spread(data: Path, out: Path, median: float = 165.0) -> Path:
    """What the lognormal assumption does to one hospital's number."""
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=160)
    xs = [i for i in range(1, 721)]
    labels = []
    for sigma, color in zip((stats.SIGMA_LOW, stats.SIGMA_DEFAULT, stats.SIGMA_HIGH), TEAL):
        mu = math.log(median)
        ys = [math.exp(-((math.log(x) - mu) ** 2) / (2 * sigma ** 2)) / (x * sigma * math.sqrt(2 * math.pi))
              for x in xs]
        ax.plot(xs, ys, color=color, linewidth=2)
        labels.append((sigma, color, *stats.interval(median, sigma, 0.8)))
    top = ax.get_ylim()[1]
    for i, (sigma, color, lo, hi) in enumerate(labels):
        y = top * (0.9 - 0.12 * i)
        ax.plot([390, 420], [y, y], color=color, linewidth=3)
        ax.text(430, y, f"σ = {sigma:.1f}: middle 80% of visits {lo:.0f}–{hi:.0f} min",
                va="center", color=INK, fontsize=8.5)
    ax.axvline(median, color=INK, linewidth=1.2)
    ax.text(median + 6, ax.get_ylim()[1] * 0.04, f"published median {median:.0f} min (data)", fontsize=8.5, color=INK)
    ax.set_title("The median is data; the spread is an assumption (CMS publishes none)",
                 fontsize=10, color=INK, loc="left")
    ax.set_xlabel("minutes in the ED for one visit (lognormal, median fixed)", fontsize=9, color=MUTED)
    ax.set_yticks([])
    ax.set_xticks(range(0, 721, 60))
    _style(ax)
    ax.yaxis.grid(False)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def chart_by_volume(data: Path, out: Path) -> Path:
    rows = load_numeric(data)
    order = ["low", "medium", "high", "very high"]
    groups = [[r["m"] for r in rows if r["edv"] == k] for k in order]
    fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=160)
    bp = ax.boxplot(groups, vert=False, widths=0.55, showfliers=False, patch_artist=True,
                    medianprops={"color": INK, "linewidth": 1.6},
                    whiskerprops={"color": MUTED}, capprops={"color": MUTED})
    for b in bp["boxes"]:
        b.set(facecolor=TEAL[0], edgecolor=TEAL[2])
    ax.set_yticks(range(1, 5), [f"{k} (n={len(g):,})" for k, g in zip(order, groups)])
    for i, g in enumerate(groups, start=1):
        q = stats.quantiles(g, [0.5])[0]
        ax.text(q, i + 0.36, f"{q:.0f}", ha="center", fontsize=8, color=INK)
    ax.set_title("Busier emergency departments run longer (OP-18b by CMS ED-volume category)",
                 fontsize=10, color=INK, loc="left")
    ax.set_xlabel("hospital median minutes; box = middle half of hospitals, whiskers 1.5 IQR", fontsize=9, color=MUTED)
    _style(ax)
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def build_charts(data: Path, docs: Path) -> list[Path]:
    docs.mkdir(parents=True, exist_ok=True)
    return [
        chart_distribution(data, docs / "op18b-distribution.png"),
        chart_assumed_spread(data, docs / "assumed-spread.png"),
        chart_by_volume(data, docs / "by-volume.png"),
    ]
