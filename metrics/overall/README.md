# Overall Behavioral Heatmap

A single unified figure summarizing all 13 OpenClaw Moltbook agents (control
baseline + 4 personality + 4 model-variant + 4 operational) on 6 normalized
behavioral metrics.

This cohort does not have its own scrape: `build_heatmap.py` reads the
already-cached aggregates from the sibling `metrics/rq2/`, `metrics/rq3/`, and
`metrics/rq4/` directories. There is no `data/` folder under `overall/` on
purpose -- one source of truth, no duplication.

## Run

```bash
cd metrics/overall
python3 build_heatmap.py     # -> figures/overall_heatmap.pdf
```

The script also echoes the final 13-row x 6-column normalized matrix to
stderr so the values in the chart are easy to spot-check.

## Agent registry

Row order on the chart, top to bottom. Canonical Moltbook usernames are kept
on disk; only the chart label varies.

| Section     | Username                  | Chart label | Source dir       |
| ----------- | ------------------------- | ----------- | ---------------- |
| Baseline    | `baselineagent`           | Control     | `metrics/rq2/`   |
| Personality | `oracle-teammoltbook`     | Oracle      | `metrics/rq2/`   |
| Personality | `explainer-teammoltbook`  | Explainer   | `metrics/rq2/`   |
| Personality | `contrarian-teammoltbook` | Contrarian  | `metrics/rq2/`   |
| Personality | `mirror-teammoltbook`     | Mirror      | `metrics/rq2/`   |
| Model       | `opus_claw`               | Opus        | `metrics/rq3/`   |
| Model       | `sonnetclaw`              | Sonnet      | `metrics/rq3/`   |
| Model       | `gpt4oclaw`               | GPT5.4      | `metrics/rq3/`   |
| Model       | `qwen_claw`               | Qwen        | `metrics/rq3/`   |
| Operational | `shan-ai`                 | Maverick    | `metrics/rq4/`   |
| Operational | `shancautious`            | Sentinel    | `metrics/rq4/`   |
| Operational | `shanamnesia`             | Drifter     | `metrics/rq4/`   |
| Operational | `shanlocked`              | Ghost       | `metrics/rq4/`   |

`baselineagent` is present under all three sibling rq dirs (same scrape, same
JSON). The registry sources it from `metrics/rq2/` only so it is never
double-counted.

## Metric definitions

Six columns, left to right on the chart.

| Metric          | Source field                                                      | Direction                            |
| --------------- | ----------------------------------------------------------------- | ------------------------------------ |
| Verbosity       | `mean_word_count` (from `agent_summary.csv`)                      | higher = wordier                     |
| Questions       | `mean_question_frequency` (from `agent_summary.csv`)              | higher = more questions              |
| Contradiction   | `mean_contradiction_ratio` (from `agent_summary.csv`)             | higher = more disagreement markers   |
| Topic Breadth   | unique `submolt` count (from `<agent>_features.json`)             | higher = wider community footprint   |
| Certainty       | `1 - minmax(mean_hedge_ratio)` (from `agent_summary.csv`)         | higher = less hedging / more direct  |
| Tone Adaptation | `1 - minmax(mean_sentiment_delta)` (from `agent_summary.csv`)     | higher = closer to parent sentiment  |

For Certainty and Tone Adaptation, the inversion is applied **after** the
min-max so the displayed value still ranges 0 to 1, with 1 meaning "best on
that axis" in plain English.

## Normalization scope

Min-max per metric column, **across all 13 agents at once**. This is
intentionally different from `metrics/rq2/`, `metrics/rq3/`, and
`metrics/rq4/`, where each radar normalizes within its own 5-agent cohort.
The unified pool is what makes a Control bar of 0.0 and a Maverick bar of 1.0
in the same column directly comparable; it also means the absolute numbers in
this heatmap will not match the per-cohort radar values one-to-one.

## Visual conventions

- Color map: `viridis`, vmin=0, vmax=1.
- Per-cell numeric annotation (two decimals), text color flipped to stay
  readable on dark vs light cells.
- White horizontal section dividers between Baseline / Personality, between
  Personality / Model, and between Model / Operational.
- Section group names ("Baseline", "Personality", "Model", "Operational")
  rendered in the left margin next to the rows they describe.

## Output

- `figures/overall_heatmap.pdf` -- the unified 13 x 6 chart, suitable for
  LaTeX inclusion alongside the per-cohort PDFs in `metrics/rq*/figures/`.
