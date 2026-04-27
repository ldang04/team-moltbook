#!/usr/bin/env python3
"""Phase 5: produce LaTeX-ready PDF charts.

Reads:  data/analysis/agent_summary.csv
        data/features/{agent}_features.json (for the scatter)
Writes: figures/rq2_word_count.pdf
        figures/rq2_linguistic_markers.pdf
        figures/rq2_mirror_adaptation.pdf
        figures/rq2_radar.pdf
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from common import (
    AGENTS,
    CONTROL_AGENT,
    DATA_ANALYSIS,
    DATA_FEATURES,
    FIGURES,
    minmax_normalize,
    read_json,
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------


def load_summary() -> list[dict[str, Any]]:
    path = DATA_ANALYSIS / "agent_summary.csv"
    if not path.exists():
        raise SystemExit(f"missing {path} — run 03_analyze.py first")
    with path.open() as fh:
        return list(csv.DictReader(fh))


def _ordered_agents(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order rows by canonical AGENTS list, then any unknowns."""
    by_name = {row["agent"]: row for row in rows}
    ordered = [by_name[a] for a in AGENTS if a in by_name]
    extras = [r for r in rows if r["agent"] not in set(AGENTS)]
    return ordered + extras


def _f(row: dict[str, Any], key: str) -> float:
    val = row.get(key, "")
    if val in (None, "", "None"):
        return 0.0
    return float(val)


def _short_label(name: str) -> str:
    return name.replace("-teammoltbook", "").replace("control1", "control")


def _color_for(name: str, default_cycle: list[str], idx: int) -> str:
    if name == CONTROL_AGENT:
        return "#888888"
    return default_cycle[idx % len(default_cycle)]


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def chart_word_count(rows: list[dict[str, Any]]) -> Path:
    rows = _ordered_agents(rows)
    labels = [_short_label(r["agent"]) for r in rows]
    means = [_f(r, "mean_word_count") for r in rows]
    stds = [_f(r, "std_word_count") for r in rows]

    cycle = plt.rcParams["axes.prop_cycle"].by_key().get("color", ["C0", "C1", "C2", "C3", "C4"])
    colors = [_color_for(r["agent"], cycle, i) for i, r in enumerate(rows)]

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    xs = np.arange(len(rows))
    ax.bar(xs, means, yerr=stds, color=colors, capsize=4, edgecolor="black", linewidth=0.5)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Mean word count per utterance")
    ax.set_title("Response length by agent (mean ± std)")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    out = FIGURES / "rq2_word_count.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


def chart_linguistic_markers(rows: list[dict[str, Any]]) -> Path:
    rows = _ordered_agents(rows)
    labels = [_short_label(r["agent"]) for r in rows]
    metrics = [
        ("Question freq", "mean_question_frequency"),
        ("Contradiction ratio", "mean_contradiction_ratio"),
        ("Hedge ratio", "mean_hedge_ratio"),
    ]

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    n_agents = len(rows)
    n_metrics = len(metrics)
    width = 0.8 / n_metrics
    xs = np.arange(n_agents)
    for i, (label, key) in enumerate(metrics):
        offset = (i - (n_metrics - 1) / 2) * width
        values = [_f(r, key) for r in rows]
        ax.bar(xs + offset, values, width=width, label=label, edgecolor="black", linewidth=0.4)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Mean ratio per utterance")
    ax.set_title("Linguistic markers by agent")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    out = FIGURES / "rq2_linguistic_markers.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


def chart_mirror_adaptation() -> Path:
    pairs: dict[str, list[tuple[float, float]]] = {
        "mirror-teammoltbook": [],
        "contrarian-teammoltbook": [],
    }
    for username in pairs:
        path = DATA_FEATURES / f"{username}_features.json"
        if not path.exists():
            continue
        payload = read_json(path)
        for u in payload.get("utterances", []):
            ps = u.get("parent_sentiment")
            if ps is None or u.get("type") != "comment":
                continue
            pairs[username].append((float(ps), float(u.get("sentiment_score") or 0.0)))

    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    style = {
        "mirror-teammoltbook": {"color": "C0", "marker": "o", "label": "Mirror"},
        "contrarian-teammoltbook": {"color": "C3", "marker": "x", "label": "Contrarian"},
    }
    for username, points in pairs.items():
        if not points:
            continue
        xs, ys = zip(*points)
        ax.scatter(xs, ys, alpha=0.5, s=20, **style[username])

    ax.plot([-1, 1], [-1, 1], color="black", linestyle="--", linewidth=0.8, label="y = x")
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)
    ax.set_xlabel("Parent sentiment (VADER compound)")
    ax.set_ylabel("Agent comment sentiment")
    ax.set_title("Tone adaptation: Mirror vs Contrarian")
    ax.axhline(0, color="gray", linewidth=0.4)
    ax.axvline(0, color="gray", linewidth=0.4)
    ax.grid(linestyle=":", alpha=0.5)
    ax.legend(loc="lower right", frameon=False)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    out = FIGURES / "rq2_mirror_adaptation.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


def chart_radar(rows: list[dict[str, Any]]) -> Path:
    rows = _ordered_agents(rows)
    by_agent = {r["agent"]: r for r in rows}

    raw_dims: list[tuple[str, dict[str, float]]] = [
        (
            "verbosity",
            {a: _f(by_agent[a], "mean_word_count") for a in by_agent},
        ),
        (
            "questions",
            {a: _f(by_agent[a], "mean_question_frequency") for a in by_agent},
        ),
        (
            "contradiction",
            {a: _f(by_agent[a], "mean_contradiction_ratio") for a in by_agent},
        ),
        (
            "certainty",
            {a: _f(by_agent[a], "mean_certainty_ratio") for a in by_agent},
        ),
    ]
    normalized: list[tuple[str, dict[str, float]]] = [
        (name, minmax_normalize(values)) for name, values in raw_dims
    ]

    # Tone adaptation = 1 - normalized mean_sentiment_delta (lower delta is better).
    deltas: dict[str, float] = {}
    for a in by_agent:
        v = by_agent[a].get("mean_sentiment_delta", "")
        deltas[a] = float(v) if v not in ("", None, "None") else 0.0
    delta_norm = minmax_normalize(deltas)
    tone_adapt = {a: 1.0 - delta_norm.get(a, 0.5) for a in by_agent}
    normalized.append(("tone_adaptation", tone_adapt))

    dim_labels = [name for name, _ in normalized]
    n_dims = len(dim_labels)
    angles = np.linspace(0, 2 * np.pi, n_dims, endpoint=False).tolist()
    angles_closed = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(6.4, 6.4), subplot_kw={"polar": True})
    cycle = plt.rcParams["axes.prop_cycle"].by_key().get("color", ["C0", "C1", "C2", "C3", "C4"])
    for i, agent in enumerate(by_agent):
        values = [normalized[d][1].get(agent, 0.0) for d in range(n_dims)]
        values_closed = values + values[:1]
        color = _color_for(agent, cycle, i)
        ax.plot(angles_closed, values_closed, color=color, linewidth=1.6, label=_short_label(agent))
        ax.fill(angles_closed, values_closed, color=color, alpha=0.12)

    ax.set_xticks(angles)
    ax.set_xticklabels(dim_labels)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.5", "0.75", "1.0"], fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_title("Personality fingerprint (min-max normalized)", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.05), frameon=False, fontsize=8)
    fig.tight_layout()
    out = FIGURES / "rq2_radar.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="Render RQ2 figures.")
    ap.parse_args()

    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = load_summary()
    log(f"wrote {chart_word_count(rows)}")
    log(f"wrote {chart_linguistic_markers(rows)}")
    log(f"wrote {chart_mirror_adaptation()}")
    log(f"wrote {chart_radar(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
