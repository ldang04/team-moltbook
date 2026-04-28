#!/usr/bin/env python3
"""Phase 5: produce LaTeX-ready PDF charts for the rq4 personas.

Reads:  data/analysis/agent_summary.csv
        data/features/{agent}_features.json (for the topic heatmap)
Writes: figures/rq4_word_count.pdf
        figures/rq4_linguistic_markers.pdf
        figures/rq4_radar.pdf
        figures/rq4_topic_heatmap.pdf

The mirror/contrarian sentiment-adaptation scatter from rq2 is intentionally
omitted because the rq4 cohort (control + Maverick / Sentinel / Drifter / Ghost)
does not include those tone-matching personas.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
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
    display_label,
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
    return display_label(name)


def _title_label(text: str) -> str:
    return (text or "unknown").replace("-", " ").replace("_", " ").title()


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
    ax.set_ylabel("Mean Word Count Per Utterance")
    ax.set_title("Response Length By Agent (Mean ± Std)")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    out = FIGURES / "rq4_word_count.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


def chart_linguistic_markers(rows: list[dict[str, Any]]) -> Path:
    rows = _ordered_agents(rows)
    labels = [_short_label(r["agent"]) for r in rows]
    metrics = [
        ("Question Frequency", "mean_question_frequency"),
        ("Contradiction Ratio", "mean_contradiction_ratio"),
        ("Hedge Ratio", "mean_hedge_ratio"),
    ]

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    n_agents = len(rows)
    n_metrics = len(metrics)
    width = 0.8 / n_metrics
    xs = np.arange(n_agents)
    max_value = 0.0
    for i, (label, key) in enumerate(metrics):
        offset = (i - (n_metrics - 1) / 2) * width
        values = [_f(r, key) for r in rows]
        max_value = max(max_value, max(values, default=0.0))
        ax.bar(xs + offset, values, width=width, label=label, edgecolor="black", linewidth=0.4)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Mean Ratio Per Utterance")
    ax.set_title("Linguistic Markers By Agent")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    # Add headroom above the tallest bar so the upper-left legend does not
    # collide with the bars (Maverick's question-frequency bar in particular).
    if max_value > 0:
        ax.set_ylim(0, max_value * 1.45)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    out = FIGURES / "rq4_linguistic_markers.pdf"
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
    ax.set_title("Personality Fingerprint (Min-Max Normalized)", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.05), frameon=False, fontsize=8)
    fig.tight_layout()
    out = FIGURES / "rq4_radar.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


def chart_topic_heatmap(rows: list[dict[str, Any]], max_topics: int = 12) -> Path:
    """Heatmap of topic/submolt engagement counts by agent."""
    rows = _ordered_agents(rows)
    agents = [r["agent"] for r in rows]
    agent_labels = [_short_label(a) for a in agents]

    counts_by_agent: dict[str, Counter[str]] = {}
    global_counts: Counter[str] = Counter()
    for agent in agents:
        path = DATA_FEATURES / f"{agent}_features.json"
        agent_counts: Counter[str] = Counter()
        if path.exists():
            payload = read_json(path)
            for utterance in payload.get("utterances", []):
                topic = (utterance.get("submolt") or "unknown").strip()
                if not topic:
                    topic = "unknown"
                agent_counts[topic] += 1
                global_counts[topic] += 1
        counts_by_agent[agent] = agent_counts

    topics = [topic for topic, _ in global_counts.most_common(max_topics)]
    if not topics:
        topics = ["unknown"]
    matrix = np.array(
        [[counts_by_agent[a].get(topic, 0) for topic in topics] for a in agents],
        dtype=float,
    )

    fig_w = max(7.2, len(topics) * 0.55)
    fig_h = max(3.8, len(agents) * 0.7)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(np.arange(len(topics)))
    ax.set_xticklabels([_title_label(topic) for topic in topics], rotation=35, ha="right")
    ax.set_yticks(np.arange(len(agents)))
    ax.set_yticklabels(agent_labels)
    ax.set_xlabel("Topic / Submolt")
    ax.set_ylabel("Agent")
    ax.set_title("Topic Engagement Heatmap (Utterance Counts)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Utterance Count")

    # Annotate smaller grids for readability.
    if matrix.size <= 160:
        vmax = float(matrix.max()) if matrix.max() > 0 else 1.0
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                value = int(matrix[i, j])
                text_color = "white" if matrix[i, j] > (0.55 * vmax) else "black"
                ax.text(j, i, f"{value}", ha="center", va="center", color=text_color, fontsize=8)

    fig.tight_layout()
    out = FIGURES / "rq4_topic_heatmap.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="Render RQ4 figures.")
    ap.parse_args()

    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = load_summary()
    log(f"wrote {chart_word_count(rows)}")
    log(f"wrote {chart_linguistic_markers(rows)}")
    log(f"wrote {chart_radar(rows)}")
    log(f"wrote {chart_topic_heatmap(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
