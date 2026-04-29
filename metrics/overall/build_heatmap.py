#!/usr/bin/env python3
"""Build the unified 13-agent OpenClaw charts.

Reads:  ../rq{2,3,4}/data/analysis/agent_summary.csv (cached aggregates)
        ../rq{2,3,4}/data/features/<username>_features.json (for topic breadth)
Writes:
  figures/overall_heatmap.pdf
  figures/overall_topic_heatmap.pdf
  figures/overall_word_count.pdf
  figures/overall_linguistic_markers.pdf

Min-max normalization is applied per metric column across all 13 agents in a
single unified pool (not per-cohort). This intentionally differs from the
rq2/rq3/rq4 radar charts, which normalize within their own 5-agent cohort,
so the absolute numbers here will not match the per-cohort radar values
one-to-one.
"""

from __future__ import annotations

import csv
from collections import Counter
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent
METRICS_ROOT = ROOT.parent
FIGURES = ROOT / "figures"


# ---------------------------------------------------------------------------
# Agent registry (row order is top -> bottom on the chart)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentSpec:
    username: str       # canonical Moltbook username (used for filenames)
    label: str          # short label rendered on the y-axis
    section: str        # group header (Baseline / Personality / Model / Operational)
    source_rq: str      # which sibling rq dir owns the cached CSV + features


AGENTS: list[AgentSpec] = [
    AgentSpec("baselineagent",            "Control",    "Baseline",    "rq2"),
    AgentSpec("oracle-teammoltbook",      "Oracle",     "Personality", "rq2"),
    AgentSpec("explainer-teammoltbook",   "Explainer",  "Personality", "rq2"),
    AgentSpec("contrarian-teammoltbook",  "Contrarian", "Personality", "rq2"),
    AgentSpec("mirror-teammoltbook",      "Mirror",     "Personality", "rq2"),
    AgentSpec("opus_claw",                "Opus",       "Model",       "rq3"),
    AgentSpec("sonnetclaw",               "Sonnet",     "Model",       "rq3"),
    AgentSpec("gpt4oclaw",                "GPT5.4",     "Model",       "rq3"),
    AgentSpec("qwen_claw",                "Qwen",       "Model",       "rq3"),
    AgentSpec("shan-ai",                  "Maverick",   "Operational", "rq4"),
    AgentSpec("shancautious",             "Sentinel",   "Operational", "rq4"),
    AgentSpec("shanamnesia",              "Drifter",    "Operational", "rq4"),
    AgentSpec("shanlocked",               "Ghost",      "Operational", "rq4"),
]


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricSpec:
    key: str                  # internal id
    title: str                # column header line 1
    descriptor: str           # column header line 2 (parenthetical)
    csv_field: str | None     # source field in agent_summary.csv (None for derived)
    invert: bool              # if True, show 1 - minmax(value)


METRICS: list[MetricSpec] = [
    MetricSpec("verbosity",       "Verbosity",       "(avg response length)",         "mean_word_count",          False),
    MetricSpec("questions",       "Questions",       "(question frequency)",          "mean_question_frequency",  False),
    MetricSpec("contradiction",   "Contradiction",   "(disagreement markers)",        "mean_contradiction_ratio", False),
    MetricSpec("topic_breadth",   "Topic Breadth",   "(unique communities)",          None,                       False),
    MetricSpec("certainty",       "Certainty",       "(low hedging / directness)",    "mean_hedge_ratio",         True),
    MetricSpec("tone_adaptation", "Tone Adaptation", "(style mirroring)",             "mean_sentiment_delta",     True),
]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _load_summary_row(rq: str, username: str) -> dict[str, str]:
    csv_path = METRICS_ROOT / rq / "data" / "analysis" / "agent_summary.csv"
    with csv_path.open() as fh:
        for row in csv.DictReader(fh):
            if row["agent"] == username:
                return row
    raise SystemExit(f"agent {username!r} not found in {csv_path}")


def _topic_breadth(rq: str, username: str) -> int:
    """Count unique submolts the agent has touched across posts + comments."""
    features_path = METRICS_ROOT / rq / "data" / "features" / f"{username}_features.json"
    payload = json.loads(features_path.read_text())
    seen: set[str] = set()
    for utterance in payload.get("utterances", []):
        topic = utterance.get("submolt")
        if isinstance(topic, str) and topic.strip():
            seen.add(topic.strip())
    return len(seen)


def _safe_float(value: str | None) -> float:
    if value in (None, "", "None"):
        return 0.0
    return float(value)


def collect_raw_matrix() -> np.ndarray:
    """Return a (n_agents, n_metrics) matrix of raw, un-normalized values."""
    matrix = np.zeros((len(AGENTS), len(METRICS)), dtype=float)
    for i, agent in enumerate(AGENTS):
        row = _load_summary_row(agent.source_rq, agent.username)
        for j, metric in enumerate(METRICS):
            if metric.csv_field is not None:
                matrix[i, j] = _safe_float(row.get(metric.csv_field))
            elif metric.key == "topic_breadth":
                matrix[i, j] = float(_topic_breadth(agent.source_rq, agent.username))
            else:
                raise RuntimeError(f"unhandled derived metric: {metric.key}")
    return matrix


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def minmax_columns(matrix: np.ndarray) -> np.ndarray:
    """Min-max each column independently across all rows. Constant columns -> 0.5."""
    out = np.zeros_like(matrix)
    for j in range(matrix.shape[1]):
        col = matrix[:, j]
        lo, hi = float(col.min()), float(col.max())
        if hi == lo:
            out[:, j] = 0.5
        else:
            out[:, j] = (col - lo) / (hi - lo)
    return out


def apply_inversions(normalized: np.ndarray) -> np.ndarray:
    out = normalized.copy()
    for j, metric in enumerate(METRICS):
        if metric.invert:
            out[:, j] = 1.0 - out[:, j]
    return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _section_breaks() -> list[int]:
    """Indices i such that AGENTS[i] is the LAST row of its section."""
    breaks: list[int] = []
    for i in range(len(AGENTS) - 1):
        if AGENTS[i].section != AGENTS[i + 1].section:
            breaks.append(i)
    return breaks


def _format_tick_number(value: float, _: float) -> str:
    return f"{value:.2f}"


def _format_count_tick_number(value: float, _: float) -> str:
    # Ticks come from geometric spacing over integer counts; round so
    # colorbars show clean integer labels.
    return f"{int(round(value))}"


def _title_label(text: str) -> str:
    return (text or "unknown").replace("-", " ").replace("_", " ").title()


def render_heatmap(values: np.ndarray, out_path: Path) -> None:
    n_rows, n_cols = values.shape
    fig_w = 1.6 * n_cols + 3.2     # extra width for left-margin section labels
    fig_h = 0.55 * n_rows + 2.4
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    positive = values[values > 0]
    norm: mcolors.LogNorm | None = None
    if positive.size:
        norm = mcolors.LogNorm(vmin=float(positive.min()), vmax=float(values.max()))
        im = ax.imshow(values, cmap="viridis", aspect="auto", norm=norm)
    else:
        im = ax.imshow(values, cmap="viridis", aspect="auto", vmin=0.0, vmax=1.0)

    ax.set_xticks(np.arange(n_cols))
    ax.set_xticklabels(
        [f"{m.title}\n{m.descriptor}" for m in METRICS],
        rotation=20,
        ha="right",
        fontsize=9,
    )
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels([a.label for a in AGENTS], fontsize=10)
    ax.tick_params(axis="x", which="both", length=0, pad=4)
    ax.tick_params(axis="y", which="both", length=0, pad=4)

    # Per-cell numeric annotations; flip color to stay readable on viridis.
    for i in range(n_rows):
        for j in range(n_cols):
            v = float(values[i, j])
            if norm is not None and v > 0:
                intensity = float(norm(v))
                color = "white" if intensity < 0.55 else "black"
            else:
                color = "white" if v < 0.55 else "black"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", color=color, fontsize=8)

    # Section dividers between groups (white lines on top of the colormap).
    for break_row in _section_breaks():
        ax.axhline(y=break_row + 0.5, color="white", linewidth=2.0, zorder=3)

    # Section group labels in the left margin, vertically centered on each group.
    section_groups: dict[str, list[int]] = {}
    for i, agent in enumerate(AGENTS):
        section_groups.setdefault(agent.section, []).append(i)
    for section, rows in section_groups.items():
        y_center = (rows[0] + rows[-1]) / 2.0
        ax.annotate(
            section,
            xy=(0, y_center),
            xycoords=("axes fraction", "data"),
            xytext=(-78, 0),
            textcoords="offset points",
            ha="right",
            va="center",
            fontsize=10,
            fontweight="bold",
        )

    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Normalized score (log color scale)", fontsize=9)
    if norm is not None:
        ticks = np.geomspace(norm.vmin, norm.vmax, num=8)
        cbar.set_ticks(ticks)
        cbar.ax.yaxis.set_major_formatter(mticker.FuncFormatter(_format_tick_number))
    else:
        cbar.set_ticks(np.linspace(0.0, 1.0, num=8))
        cbar.ax.yaxis.set_major_formatter(mticker.FuncFormatter(_format_tick_number))
    cbar.ax.tick_params(labelsize=8)

    # Stack the title and italic subtitle as figure-level text so they sit
    # cleanly above the axes without colliding with each other or the
    # heatmap top edge. `top=0.86` reserves enough headroom for both lines.
    fig.suptitle(
        "Unified Behavioral Heatmap Across All Agents",
        fontsize=13,
        y=0.965,
    )
    fig.text(
        0.5,
        0.915,
        "Normalized behavioral metrics (0 = lowest among agents, 1 = highest)",
        ha="center",
        va="center",
        fontsize=9,
        style="italic",
        color="#444444",
    )
    fig.text(
        0.5,
        0.03,
        "* Color scale uses log-scaled values to make small differences more visible.",
        ha="center",
        va="bottom",
        fontsize=8,
        color="#444444",
    )

    # Make room for the left-margin section labels, rotated x-tick text, and
    # the two-line title block above the heatmap.
    fig.subplots_adjust(left=0.22, right=0.94, top=0.86, bottom=0.20)
    fig.savefig(out_path)
    plt.close(fig)


def render_topic_heatmap(max_topics: int = 12) -> Path:
    """Heatmap of topic/submolt utterance counts by agent (log color scale)."""
    counts_by_agent: dict[str, Counter[str]] = {}
    global_counts: Counter[str] = Counter()

    for agent in AGENTS:
        features_path = (
            METRICS_ROOT
            / agent.source_rq
            / "data"
            / "features"
            / f"{agent.username}_features.json"
        )
        agent_counts: Counter[str] = Counter()
        if features_path.exists():
            payload = json.loads(features_path.read_text())
            for utterance in payload.get("utterances", []):
                topic_raw = utterance.get("submolt") or "unknown"
                topic = topic_raw if isinstance(topic_raw, str) else "unknown"
                topic = topic.strip() if topic else "unknown"
                agent_counts[topic] += 1
                global_counts[topic] += 1
        counts_by_agent[agent.username] = agent_counts

    topics = [topic for topic, _ in global_counts.most_common(max_topics)]
    if not topics:
        topics = ["unknown"]

    agent_usernames = [a.username for a in AGENTS]
    matrix = np.array(
        [[counts_by_agent[a].get(topic, 0) for topic in topics] for a in agent_usernames],
        dtype=float,
    )

    fig_w = max(7.2, len(topics) * 0.55)
    fig_h = max(3.8, len(agent_usernames) * 0.7)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    positive = matrix[matrix > 0]
    norm: mcolors.LogNorm | None = None
    if positive.size:
        norm = mcolors.LogNorm(vmin=float(positive.min()), vmax=float(positive.max()))
        im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", norm=norm)
    else:
        im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd")

    ax.set_xticks(np.arange(len(topics)))
    ax.set_xticklabels([_title_label(topic) for topic in topics], rotation=35, ha="right")
    ax.set_yticks(np.arange(len(agent_usernames)))
    ax.set_yticklabels([a.label for a in AGENTS])
    ax.set_xlabel("Topic / Submolt")
    ax.set_ylabel("Agent")
    ax.set_title("Topic Engagement Heatmap (Utterance Counts)")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Utterance Count (log scale)")
    if norm is not None:
        ticks = np.geomspace(norm.vmin, norm.vmax, num=8)
        cbar.set_ticks(ticks)
        cbar.ax.yaxis.set_major_formatter(mticker.FuncFormatter(_format_count_tick_number))
    else:
        vmax = float(matrix.max()) if matrix.max() > 0 else 1.0
        cbar.set_ticks(np.linspace(0.0, vmax, num=8))
        cbar.ax.yaxis.set_major_formatter(mticker.FuncFormatter(_format_count_tick_number))

    # Annotate smaller grids for readability.
    if matrix.size <= 160:
        vmax = float(matrix.max()) if matrix.max() > 0 else 1.0
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                value = int(matrix[i, j])
                if norm is not None and value > 0:
                    intensity = float(norm(matrix[i, j]))
                    text_color = "white" if intensity > 0.55 else "black"
                else:
                    text_color = "white" if matrix[i, j] > (0.55 * vmax) else "black"
                ax.text(
                    j,
                    i,
                    f"{value}",
                    ha="center",
                    va="center",
                    color=text_color,
                    fontsize=8,
                )

    fig.text(
        0.5,
        0.01,
        "* Color scale uses log-scaled utterance counts to make small differences more visible.",
        ha="center",
        va="bottom",
        fontsize=8,
        color="#444444",
    )

    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out = FIGURES / "overall_topic_heatmap.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


def render_word_count_chart() -> Path:
    """Bar chart of mean word count per utterance, across all 13 agents."""
    xs = np.arange(len(AGENTS))
    labels = [a.label for a in AGENTS]
    means: list[float] = []
    stds: list[float] = []

    for agent in AGENTS:
        row = _load_summary_row(agent.source_rq, agent.username)
        means.append(_safe_float(row.get("mean_word_count")))
        stds.append(_safe_float(row.get("std_word_count")))

    cycle = plt.rcParams["axes.prop_cycle"].by_key().get(
        "color", ["C0", "C1", "C2", "C3", "C4", "C5", "C6"]
    )
    colors = [cycle[i % len(cycle)] for i in range(len(AGENTS))]

    fig, ax = plt.subplots(figsize=(10.5, 4.7))
    ax.bar(xs, means, yerr=stds, color=colors, capsize=4, edgecolor="black", linewidth=0.5)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Mean Word Count Per Utterance")
    ax.set_title("Response Length By Agent (Mean ± Std)")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    out = FIGURES / "overall_word_count.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


def render_linguistic_markers_chart() -> Path:
    """Grouped bar chart of the three core linguistic marker metrics."""
    metrics: list[tuple[str, str]] = [
        ("Questions", "mean_question_frequency"),
        ("Contradiction Ratio", "mean_contradiction_ratio"),
        ("Hedge Ratio", "mean_hedge_ratio"),
    ]

    xs = np.arange(len(AGENTS))
    labels = [a.label for a in AGENTS]

    fig, ax = plt.subplots(figsize=(12.2, 5.0))
    n_metrics = len(metrics)
    width = 0.8 / n_metrics
    cycle = plt.rcParams["axes.prop_cycle"].by_key().get(
        "color", ["C0", "C1", "C2", "C3", "C4", "C5"]
    )

    for i, (label, key) in enumerate(metrics):
        offset = (i - (n_metrics - 1) / 2) * width
        values: list[float] = []
        for agent in AGENTS:
            row = _load_summary_row(agent.source_rq, agent.username)
            values.append(_safe_float(row.get(key)))
        ax.bar(
            xs + offset,
            values,
            width=width,
            label=label,
            edgecolor="black",
            linewidth=0.4,
            color=cycle[i % len(cycle)],
        )

    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Mean Ratio Per Utterance")
    ax.set_title("Linguistic Markers By Agent")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()

    out = FIGURES / "overall_linguistic_markers.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    raw = collect_raw_matrix()
    normalized = minmax_columns(raw)
    final = apply_inversions(normalized)

    # Echo the per-agent row to stderr for debuggability.
    log("Unified heatmap values (rows = agents, columns = metrics):")
    header = ["agent"] + [m.key for m in METRICS]
    log("  " + " | ".join(f"{c:>16}" for c in header))
    for i, agent in enumerate(AGENTS):
        cells = [f"{final[i, j]:.2f}" for j in range(len(METRICS))]
        log("  " + " | ".join([f"{agent.label:>16}", *[f"{c:>16}" for c in cells]]))

    out = FIGURES / "overall_heatmap.pdf"
    render_heatmap(final, out)
    log(f"wrote {out}")

    out_topic = render_topic_heatmap()
    log(f"wrote {out_topic}")

    out_word = render_word_count_chart()
    log(f"wrote {out_word}")

    out_markers = render_linguistic_markers_chart()
    log(f"wrote {out_markers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
