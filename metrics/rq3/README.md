# RQ3 Moltbook Linguistic Analysis

Same scrape -> features -> aggregate -> visualize pipeline as `metrics/rq2`
and `metrics/rq4`, pointed at a different cohort: the OpenClaw control
baseline plus four model-backed variants of the same persona run on
different underlying LLMs (Opus, Sonnet, GPT-4o, Qwen). The figures are
labelled with the model-variant names; the underlying CSV/JSON files keep
the canonical Moltbook usernames for reproducibility.

## Setup

```bash
cd metrics/rq3
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m textblob.download_corpora    # one-time, for subjectivity scoring
cp .env.example .env                   # then fill in MOLTBOOK_API_KEY
```

The API key is read from the `MOLTBOOK_API_KEY` environment variable. The
scripts also load `.env` (the same tiny built-in parser as rq2/rq4). Never
commit a real key.

## Run

```bash
python 01_scrape.py     # -> data/raw/{agent}.json
python 02_features.py   # -> data/features/{agent}_features.json
python 03_analyze.py    # -> data/analysis/{agent_summary.csv, fidelity_report.json}
python 04_visualize.py  # -> figures/rq3_*.pdf
```

Each script accepts `--agents a,b,c` to scope to a subset and `--help` for
all options. `01_scrape.py` is resumable (skips agents whose raw JSON already
exists, unless `--force`).

## Agents and display labels

Defined in `common.py`:

| Moltbook username | Chart label | Source                                  |
| ----------------- | ----------- | --------------------------------------- |
| `baselineagent`   | `M-gemini 2.5 flash (Control)` | https://www.moltbook.com/u/baselineagent |
| `opus_claw`       | `M-Opus`    | https://www.moltbook.com/u/opus_claw    |
| `sonnetclaw`      | `M-Sonnet`  | https://www.moltbook.com/u/sonnetclaw   |
| `gpt4oclaw`       | `M-gpt5.4`  | https://www.moltbook.com/u/gpt4oclaw    |
| `qwen_claw`       | `M-Qwen`    | https://www.moltbook.com/u/qwen_claw    |

Display labels are applied in the visualizer via `display_label()` from
`common.py`. The on-disk filenames (`data/raw/<username>.json`,
`data/features/<username>_features.json`) and the `agent` column in
`data/analysis/agent_summary.csv` always use the canonical Moltbook
username so the data is portable to other tooling.

## Differences from rq2 / rq4

- Cohort is control + four model-variant agents (same persona spec on
  different underlying LLMs) instead of the four hand-designed personas
  (rq2) or four exploratory personas (rq4).
- `chart_mirror_adaptation` is omitted because there's no Mirror or
  Contrarian agent in this cohort to compare against.
- `03_analyze.py` ships an empty `CHECKS` list: rq3 is a model-variant
  comparison, not a per-agent fidelity check, so the fidelity report is
  generated but contains zero checks. The summary CSV still aggregates
  every metric.

## Outputs

- `data/raw/{agent}.json` - raw posts and comments with resolved parents
- `data/features/{agent}_features.json` - utterance-level linguistic features
- `data/analysis/agent_summary.csv` - per-agent aggregates
- `data/analysis/fidelity_report.json` - empty `checks` array for rq3
- `figures/rq3_word_count.pdf`
- `figures/rq3_linguistic_markers.pdf`
- `figures/rq3_radar.pdf`
- `figures/rq3_topic_heatmap.pdf` - agent x topic/submolt engagement heatmap
