#!/usr/bin/env python3
"""Phase 2: compute per-utterance linguistic features.

Reads:  data/raw/{agent}.json
Writes: data/features/{agent}_features.json
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from common import (
    AGENTS,
    CERTAINTY_PHRASES,
    CONTRADICTION_PHRASES,
    DATA_FEATURES,
    DATA_RAW,
    HEDGE_PHRASES,
    avg_word_length,
    count_formatting_elements,
    count_negations,
    count_phrases,
    has_bullets,
    has_headers,
    jaccard_overlap,
    parse_agent_arg,
    read_json,
    safe_div,
    split_sentences,
    textblob_subjectivity,
    tokenize_words,
    vader_compound,
    write_json,
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def compute_features(utterance: dict[str, Any]) -> dict[str, Any]:
    body: str = utterance.get("body") or ""
    parent_body: str | None = utterance.get("parent_body")

    tokens = tokenize_words(body)
    word_count = len(tokens)
    sentences = split_sentences(body)
    sentence_count = max(len(sentences), 1) if body.strip() else 0
    sent_denom = sentence_count or 1

    hedge_count = count_phrases(body, HEDGE_PHRASES)
    certainty_count = count_phrases(body, CERTAINTY_PHRASES)
    contradiction_count = count_phrases(body, CONTRADICTION_PHRASES)
    negation_count = count_negations(body)

    sentiment_score = vader_compound(body)
    subjectivity_score = textblob_subjectivity(body)

    features: dict[str, Any] = {
        # Structure
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": safe_div(word_count, sent_denom),
        "has_bullets": has_bullets(body),
        "has_headers": has_headers(body),
        "formatting_density": safe_div(
            count_formatting_elements(body), max(word_count, 1)
        ),
        # Questions / hedging / certainty
        "question_frequency": safe_div(body.count("?"), sent_denom),
        "hedge_count": hedge_count,
        "certainty_count": certainty_count,
        "hedge_ratio": safe_div(hedge_count, max(word_count, 1)),
        "certainty_ratio": safe_div(certainty_count, max(word_count, 1)),
        # Disagreement
        "contradiction_count": contradiction_count,
        "contradiction_ratio": safe_div(contradiction_count, sent_denom),
        "negation_count": negation_count,
        # Sentiment
        "sentiment_score": sentiment_score,
        "subjectivity_score": subjectivity_score,
        # Mirror-specific (filled in below if parent present)
        "parent_sentiment": None,
        "sentiment_delta": None,
        "lexical_overlap": None,
        "register_match": None,
    }

    if parent_body:
        parent_sent = vader_compound(parent_body)
        features["parent_sentiment"] = parent_sent
        features["sentiment_delta"] = abs(sentiment_score - parent_sent)
        features["lexical_overlap"] = jaccard_overlap(body, parent_body)
        features["register_match"] = (
            abs(avg_word_length(body) - avg_word_length(parent_body)) <= 0.5
        )

    return features


def featurize_agent(username: str) -> int:
    in_path = DATA_RAW / f"{username}.json"
    if not in_path.exists():
        log(f"[{username}] missing {in_path} — run 01_scrape.py first")
        return 0
    raw = read_json(in_path)
    rows: list[dict[str, Any]] = []
    utterances = raw.get("utterances", [])
    for u in utterances:
        merged = {**u, **compute_features(u)}
        rows.append(merged)
    out_path = DATA_FEATURES / f"{username}_features.json"
    write_json(
        out_path,
        {
            "agent": username,
            "profile": raw.get("profile"),
            "utterances": rows,
        },
    )
    log(f"[{username}] featurized {len(rows)} utterances -> {out_path}")
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Featurize scraped Moltbook utterances.")
    ap.add_argument("--agents", help="Comma-separated agents", default=None)
    args = ap.parse_args()

    DATA_FEATURES.mkdir(parents=True, exist_ok=True)
    for username in parse_agent_arg(args.agents):
        featurize_agent(username)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
