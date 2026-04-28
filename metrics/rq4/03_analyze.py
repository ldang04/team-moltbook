#!/usr/bin/env python3
"""Phase 3 + 4: aggregate per-agent stats and run the fidelity report.

Reads:  data/features/{agent}_features.json
Writes: data/analysis/agent_summary.csv
        data/analysis/fidelity_report.json
"""

from __future__ import annotations

import argparse
import csv
import statistics as stats
import sys
from typing import Any

from common import (
    AGENTS,
    DATA_ANALYSIS,
    DATA_FEATURES,
    parse_agent_arg,
    read_json,
    write_json,
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

DISTRIBUTION_FIELDS = [
    "word_count",
    "sentence_count",
    "question_frequency",
    "hedge_ratio",
    "certainty_ratio",
    "contradiction_ratio",
    "sentiment_score",
]

NUMERIC_FIELDS = DISTRIBUTION_FIELDS + ["negation_count"]


def _stat(values: list[float], op: str) -> float:
    if not values:
        return 0.0
    if op == "mean":
        return float(stats.fmean(values))
    if op == "median":
        return float(stats.median(values))
    if op == "std":
        return float(stats.pstdev(values)) if len(values) > 1 else 0.0
    raise ValueError(op)


def aggregate_agent(payload: dict[str, Any]) -> dict[str, Any]:
    utterances: list[dict[str, Any]] = payload.get("utterances", [])
    n_total = len(utterances)
    n_posts = sum(1 for u in utterances if u.get("type") == "post")
    n_comments = sum(1 for u in utterances if u.get("type") == "comment")

    row: dict[str, Any] = {
        "agent": payload.get("agent"),
        "n_total": n_total,
        "n_posts": n_posts,
        "n_comments": n_comments,
    }

    for field in DISTRIBUTION_FIELDS:
        vals = [float(u.get(field) or 0) for u in utterances]
        row[f"mean_{field}"] = _stat(vals, "mean")
        row[f"median_{field}"] = _stat(vals, "median")
        row[f"std_{field}"] = _stat(vals, "std")

    negs = [float(u.get("negation_count") or 0) for u in utterances]
    row["mean_negation_count"] = _stat(negs, "mean")

    formatted = sum(
        1 for u in utterances if u.get("has_bullets") or u.get("has_headers")
    )
    row["formatting_rate"] = (formatted / n_total) if n_total else 0.0

    deltas = [float(u["sentiment_delta"]) for u in utterances if u.get("sentiment_delta") is not None]
    overlaps = [float(u["lexical_overlap"]) for u in utterances if u.get("lexical_overlap") is not None]
    row["mean_sentiment_delta"] = _stat(deltas, "mean") if deltas else None
    row["mean_lexical_overlap"] = _stat(overlaps, "mean") if overlaps else None
    row["n_with_parent"] = len(deltas)

    return row


# ---------------------------------------------------------------------------
# Fidelity report
# ---------------------------------------------------------------------------

# Each check: which agent should rank where on which metric.
# criterion: "lowest" | "highest" | "top2" (rank within top 2).
#
# rq4 has no a-priori per-persona expectations (Maverick / Sentinel / Drifter /
# Ghost are exploratory rather than designed-to-spec), so we leave CHECKS
# empty. The fidelity report still gets written so the file layout matches
# rq2; it just contains zero checks.
CHECKS: list[dict[str, Any]] = []


def _rank(values: dict[str, float], criterion: str) -> list[str]:
    items = [(k, v) for k, v in values.items() if v is not None]
    if criterion == "lowest":
        items.sort(key=lambda kv: kv[1])
    else:  # highest, top2
        items.sort(key=lambda kv: kv[1], reverse=True)
    return [k for k, _ in items]


def run_fidelity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_agent = {row["agent"]: row for row in rows}
    report: list[dict[str, Any]] = []
    for check in CHECKS:
        metric = check["metric"]
        values = {agent: row.get(metric) for agent, row in by_agent.items()}
        ranking = _rank(values, check["criterion"])
        actual_top = ranking[0] if ranking else None
        if check["criterion"] == "top2":
            passed = check["expected_agent"] in ranking[:2]
        else:
            passed = actual_top == check["expected_agent"]
        report.append(
            {
                "check_id": check["check_id"],
                "description": check["description"],
                "expected_agent": check["expected_agent"],
                "metric": metric,
                "criterion": check["criterion"],
                "actual_top_agent": actual_top,
                "ranking": ranking,
                "passed": passed,
                "values": {k: (None if v is None else float(v)) for k, v in values.items()},
            }
        )
    return report


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------


def _csv_columns(rows: list[dict[str, Any]]) -> list[str]:
    leading = ["agent", "n_total", "n_posts", "n_comments", "n_with_parent"]
    metric_cols: list[str] = []
    for field in DISTRIBUTION_FIELDS:
        metric_cols += [f"mean_{field}", f"median_{field}", f"std_{field}"]
    metric_cols += [
        "mean_negation_count",
        "formatting_rate",
        "mean_sentiment_delta",
        "mean_lexical_overlap",
    ]
    cols = leading + metric_cols
    # Preserve any unexpected extras at the end.
    seen = set(cols)
    for row in rows:
        for k in row:
            if k not in seen:
                cols.append(k)
                seen.add(k)
    return cols


def write_summary_csv(rows: list[dict[str, Any]], path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = _csv_columns(rows)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in rows:
            normalized = {k: row.get(k, "") for k in cols}
            w.writerow(normalized)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate features and produce fidelity report.")
    ap.add_argument("--agents", help="Comma-separated agents", default=None)
    args = ap.parse_args()

    DATA_ANALYSIS.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for username in parse_agent_arg(args.agents):
        in_path = DATA_FEATURES / f"{username}_features.json"
        if not in_path.exists():
            log(f"[{username}] missing {in_path} — run 02_features.py first")
            continue
        payload = read_json(in_path)
        rows.append(aggregate_agent(payload))

    if not rows:
        log("no agent feature files found; aborting")
        return 1

    summary_path = DATA_ANALYSIS / "agent_summary.csv"
    write_summary_csv(rows, summary_path)
    log(f"wrote {summary_path} ({len(rows)} agents)")

    report = run_fidelity(rows)
    report_path = DATA_ANALYSIS / "fidelity_report.json"
    passed = sum(1 for r in report if r["passed"])
    write_json(
        report_path,
        {
            "summary": {
                "total_checks": len(report),
                "passed": passed,
                "failed": len(report) - passed,
            },
            "checks": report,
        },
    )
    log(f"wrote {report_path} ({passed}/{len(report)} checks passed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
