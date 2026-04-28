# RQ4 Moltbook Linguistic Analysis

Same scrape -> features -> aggregate -> visualize pipeline as `metrics/rq2`,
pointed at a different cohort: the OpenClaw control baseline plus four
exploratory personas (Maverick, Sentinel, Drifter, Ghost). The figures are
labelled with the persona names; the underlying CSV/JSON files keep the
canonical Moltbook usernames for reproducibility.

## Setup

```bash
cd metrics/rq4
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m textblob.download_corpora    # one-time, for subjectivity scoring
cp .env.example .env                   # then fill in MOLTBOOK_API_KEY
```

The API key is read from the `MOLTBOOK_API_KEY` environment variable. The
scripts also load `.env` (the same tiny built-in parser as rq2). Never
commit a real key.

## Run

```bash
python 01_scrape.py     # -> data/raw/{agent}.json
python 02_features.py   # -> data/features/{agent}_features.json
python 03_analyze.py    # -> data/analysis/{agent_summary.csv, fidelity_report.json}
python 04_visualize.py  # -> figures/rq4_*.pdf
```

Each script accepts `--agents a,b,c` to scope to a subset and `--help` for
all options. `01_scrape.py` is resumable (skips agents whose raw JSON already
exists, unless `--force`).

## Agents and display labels

Defined in `common.py`:

| Moltbook username | Chart label | Source                                     |
| ----------------- | ----------- | ------------------------------------------ |
| `baselineagent`   | `control`   | https://www.moltbook.com/u/baselineagent   |
| `shan-ai`         | `Maverick`  | https://www.moltbook.com/u/shan-ai         |
| `shancautious`    | `Sentinel`  | https://www.moltbook.com/u/shancautious    |
| `shanamnesia`     | `Drifter`   | https://moltbook.com/u/shanamnesia         |
| `shanlocked`      | `Ghost`     | https://www.moltbook.com/u/shanlocked      |

Display labels are applied in the visualizer via `display_label()` from
`common.py`. The on-disk filenames (`data/raw/<username>.json`,
`data/features/<username>_features.json`) and the `agent` column in
`data/analysis/agent_summary.csv` always use the canonical Moltbook
username so the data is portable to other tooling.

## Differences from rq2

- Cohort is control + four exploratory personas instead of the four
  hand-designed `*-teammoltbook` personas plus the control.
- `chart_mirror_adaptation` is omitted because there's no Mirror or
  Contrarian agent in this cohort to compare against.
- `03_analyze.py` ships an empty `CHECKS` list: the rq4 personas have no
  documented per-metric expectations, so the fidelity report is generated
  but contains zero checks. The summary CSV still aggregates every metric.

## Outputs

- `data/raw/{agent}.json` - raw posts and comments with resolved parents
- `data/features/{agent}_features.json` - utterance-level linguistic features
- `data/analysis/agent_summary.csv` - per-agent aggregates
- `data/analysis/fidelity_report.json` - empty `checks` array for rq4
- `figures/rq4_word_count.pdf`
- `figures/rq4_linguistic_markers.pdf`
- `figures/rq4_radar.pdf`
- `figures/rq4_topic_heatmap.pdf` - agent x topic/submolt engagement heatmap
