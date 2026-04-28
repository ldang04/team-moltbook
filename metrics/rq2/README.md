# RQ2 Moltbook Linguistic Analysis

Scrapes public Moltbook content for the RQ2 agents, computes per-utterance
linguistic features, aggregates per agent, runs a fidelity report against
expected personality signatures, and emits LaTeX-ready PDF charts.

## Setup

```bash
cd research/rq2
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m textblob.download_corpora    # one-time, for subjectivity scoring
cp .env.example .env                   # then fill in MOLTBOOK_API_KEY
```

The API key is read from the `MOLTBOOK_API_KEY` environment variable. The
scripts also load `.env` (a tiny built-in parser, no `python-dotenv`
dependency). Never commit a real key.

## Run

```bash
python 01_scrape.py     # -> data/raw/{agent}.json
python 02_features.py   # -> data/features/{agent}_features.json
python 03_analyze.py    # -> data/analysis/{agent_summary.csv, fidelity_report.json}
python 04_visualize.py  # -> figures/rq2_*.pdf
```

Each script accepts `--agents a,b,c` to scope to a subset and `--help` for
all options. `01_scrape.py` is resumable (skips agents whose raw JSON already
exists, unless `--force`).

## Agents

Defined in `common.py`:

- `oracle-teammoltbook`
- `explainer-teammoltbook`
- `contrarian-teammoltbook`
- `mirror-teammoltbook`
- `baselineagent` (control baseline; rendered as "control" in figures)

## Moltbook API endpoints used

The scraper hits the live Moltbook API at `https://www.moltbook.com/api/v1`:

- `GET /agents/{username}/profile` - id, karma, posts/comments counts
- `GET /posts?author={username}&sort=new&limit=50` - paginated via `has_more` + `next_cursor`
- `GET /agents/{username}/comments?limit=500` - single page, returns up to limit
- `GET /posts/{post_id}` - resolves parent post body (title + content) for tone-matching analysis

User-comment rows only expose their parent post (not parent comment), so
the parent body for Mirror/Contrarian tone analysis is `post.title + post.content`.

## Note on the control agent

`baselineagent` is the OpenClaw baseline agent (rendered as "control" in
the figures). It has organic Moltbook activity, so it shows up in the
summary CSV and figures with real values rather than a row of zeros. It
serves as a no-persona reference point against which the four targeted
personas (oracle / explainer / contrarian / mirror) are compared.

## Outputs

- `data/raw/{agent}.json` - raw posts and comments with resolved parents
- `data/features/{agent}_features.json` - utterance-level linguistic features
- `data/analysis/agent_summary.csv` - per-agent aggregates
- `data/analysis/fidelity_report.json` - pass/fail per expected signature
- `figures/rq2_word_count.pdf`
- `figures/rq2_linguistic_markers.pdf`
- `figures/rq2_mirror_adaptation.pdf`
- `figures/rq2_radar.pdf`
- `figures/rq2_topic_heatmap.pdf` - agent x topic/submolt engagement heatmap
